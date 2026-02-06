import SwiftUI
import UniformTypeIdentifiers

// MARK: - View Model
@MainActor
class StudioViewModel: ObservableObject {
    @Published var jobs: [Job] = []
    @Published var isLoading = false
    @Published var isLoadingMore = false
    @Published var errorMessage: String?

    let studio: Studio
    private var nextStartIndex = 1
    private let pageSize = 10
    private var totalJobs = 0
    
    var canLoadMore: Bool {
        false // Generic scraper doesn't support pagination yet
    }

    init(studio: Studio) {
        self.studio = studio
    }

    func fetchJobs(isRefresh: Bool) async {
        if isRefresh {
            guard !isLoading else { return }
            isLoading = true
            // On refresh, reset everything
            nextStartIndex = 1
            totalJobs = 0
            jobs = []
        } else {
            // This is a subsequent load
            guard !isLoadingMore && canLoadMore else { return }
            isLoadingMore = true
        }
        
        errorMessage = nil
        
        do {
            let result = try await JobScraper.shared.fetchJobs(for: studio, startingAt: nextStartIndex)
            
            // Using a dictionary to ensure no duplicates are added
            var uniqueJobs = Dictionary(uniqueKeysWithValues: jobs.map { ($0.id, $0) })
            result.jobs.forEach { uniqueJobs[$0.id] = $0 }
            
            self.jobs = Array(uniqueJobs.values).sorted(by: { $0.title < $1.title }) // Keep a consistent order
            
            self.totalJobs = result.total
            self.nextStartIndex += self.pageSize
            
        } catch {
            self.errorMessage = error.localizedDescription
            print("Error fetching jobs for \(studio.name): \(error)")
        }
        
        if isRefresh {
            isLoading = false
        } else {
            isLoadingMore = false
        }
    }
    
    func filteredJobs(filterText: String) -> [Job] {
        if filterText.isEmpty {
            return jobs
        }
        return jobs.filter {
            $0.title.range(of: filterText, options: [.caseInsensitive, .diacriticInsensitive]) != nil
        }
    }
}

// MARK: - Main Content View
struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var studios: [Studio] = []
    @State private var filterText = ""
    @State private var studioSearchText = ""
    @State private var disabledStudioIDs: Set<String> = []
    @State private var navigationVisibility = NavigationSplitViewVisibility.all
    @State private var viewModels: [String: StudioViewModel] = [:]
    @State private var hideEmpty = false
    @State private var scrollToStudioID: String? = nil
    
    @FocusState private var isJobFilterFocused: Bool

    private var filteredStudios: [Studio] {
        if studioSearchText.isEmpty {
            return studios
        }
        return studios.filter {
            $0.name.range(of: studioSearchText, options: [.caseInsensitive, .diacriticInsensitive]) != nil
        }
    }
    
    private var visibleStudios: [Studio] {
        studios.filter { !disabledStudioIDs.contains($0.id) }
    }
    
    private var sidebarView: some View {
        VStack {
            ClearableTextField(placeholder: "Search studios...", text: $studioSearchText)
                .padding([.horizontal, .top])

            List {
                ForEach(filteredStudios) { studio in
                    studioToggleRow(for: studio)
                }
                .onMove(perform: studioSearchText.isEmpty ? moveStudioInSidebar : nil)
            }
            .scrollContentBackground(.hidden)
            .listStyle(.sidebar)
        }
        .padding(8)
        .navigationSplitViewColumnWidth(250)
        .navigationTitle("Studios")
        .background(Material.ultraThinMaterial)
    }
    
    private func studioToggleRow(for studio: Studio) -> some View {
        HStack {
            Image(systemName: "line.3.horizontal")
                .foregroundColor(.secondary)
            Toggle(isOn: Binding(
                get: { !disabledStudioIDs.contains(studio.id) },
                set: { isEnabled in
                    if isEnabled {
                        disabledStudioIDs.remove(studio.id)
                    } else {
                        disabledStudioIDs.insert(studio.id)
                    }
                    updateViewModels()
                    saveDisabledStudios()
                }
            )) {
                Text(studio.name)
                    .font(.headline)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        if !disabledStudioIDs.contains(studio.id) {
                            scrollToStudioID = studio.id
                        }
                    }
                    .pointingCursor()
            }
        }
        .listRowBackground(Color.clear)
    }

    var body: some View {
        NavigationSplitView(columnVisibility: $navigationVisibility) {
            sidebarView
        } detail: {
            StudioGridView(
                studios: $studios,
                visibleStudios: visibleStudios,
                viewModels: viewModels,
                filterText: $filterText,
                hideEmpty: $hideEmpty,
                scrollToID: $scrollToStudioID,
                isJobFilterFocused: $isJobFilterFocused,
                reloadAllAction: reloadAll,
                saveOrderAction: saveStudiosOrder
            )
            .background(Material.ultraThinMaterial)
        }
        .onAppear {
            loadData()
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                isJobFilterFocused = true
            }
        }
        .onChange(of: appState.disabledStudioIDs) { _, newValue in
            disabledStudioIDs = newValue
            updateViewModels()
        }
        .onChange(of: disabledStudioIDs) { _, newValue in
            appState.disabledStudioIDs = newValue
            saveDisabledStudios()
        }
        .sheet(isPresented: $appState.showAbout) {
            AboutView()
        }
        .alert("Database Update", isPresented: $appState.showUpdateAlert) {
            Button("OK") {
                if appState.updateMessage?.contains("updated") == true {
                    loadData()
                }
            }
        } message: {
            Text(appState.updateMessage ?? "")
        }
        .alert("Refetch All Logos", isPresented: $appState.showLogoRefreshAlert) {
            Button("Cancel", role: .cancel) { }
            Button("Refetch", role: .destructive) {
                Task {
                    await appState.refetchAllLogos()
                }
            }
        } message: {
            Text("This will clear all cached studio logos and download them again. Are you sure?")
        }
        .onChange(of: appState.studios) { _, newValue in
            studios = newValue
            updateViewModels()
        }
        .overlay {
            if appState.isUpdatingDatabase {
                ZStack {
                    Color.black.opacity(0.4)
                        .ignoresSafeArea()
                    
                    VStack(spacing: 20) {
                        ProgressView()
                            .scaleEffect(1.5)
                        
                        Text("Updating Studios Database...")
                            .font(.headline)
                        
                        Text("Fetching latest studio configurations from GitHub")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(40)
                    .background(.ultraThinMaterial)
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
                    .shadow(radius: 20)
                }
                .transition(.opacity)
            }
        }
        .animation(.default, value: appState.isUpdatingDatabase)
    }

    // MARK: Data Helpers
    private func loadData() {
        // Initial load from whatever we have (App Support or Bundle)
        self.studios = ConfigManager.shared.loadStudios()
        appState.studios = self.studios
        loadDisabledStudios()
        disabledStudioIDs = appState.disabledStudioIDs
        updateViewModels()
        
        // Force an update check every time we load data
        Task {
            let updated = await ConfigManager.shared.updateConfigIfNeeded()
            if updated {
                await MainActor.run {
                    self.studios = ConfigManager.shared.loadStudios()
                    appState.studios = self.studios
                    updateViewModels()
                }
            }
        }
    }

    private func loadDisabledStudios() {
        if let savedIDs = UserDefaults.standard.stringArray(forKey: "disabledStudioIDs") {
            self.disabledStudioIDs = Set(savedIDs)
        }
    }

    private func saveStudiosOrder() {
        let orderedIDs = studios.map { $0.id }
        UserDefaults.standard.set(orderedIDs, forKey: "studioOrder")
    }
    
    private func saveDisabledStudios() {
        UserDefaults.standard.set(Array(disabledStudioIDs), forKey: "disabledStudioIDs")
    }
    
    private func updateViewModels() {
        let visibleIDs = Set(studios.filter { !disabledStudioIDs.contains($0.id) }.map { $0.id })
        
        // Remove view models for studios that are no longer visible
        for id in viewModels.keys {
            if !visibleIDs.contains(id) {
                viewModels.removeValue(forKey: id)
            }
        }
        
        // Add view models for newly visible studios
        for id in visibleIDs {
            if viewModels[id] == nil {
                if let studio = studios.first(where: { $0.id == id }) {
                    viewModels[id] = StudioViewModel(studio: studio)
                }
            }
        }
    }
    
    private func reloadAll() async {
        await withTaskGroup(of: Void.self) { group in
            for viewModel in viewModels.values {
                group.addTask {
                    await viewModel.fetchJobs(isRefresh: true)
                }
            }
        }
    }
    
    private func moveStudioInSidebar(from source: IndexSet, to destination: Int) {
        studios.move(fromOffsets: source, toOffset: destination)
        saveStudiosOrder()
    }
}

// MARK: - Grid View
struct StudioGridView: View {
    @Binding var studios: [Studio]
    let visibleStudios: [Studio]
    let viewModels: [String: StudioViewModel]
    @Binding var filterText: String
    @Binding var hideEmpty: Bool
    @Binding var scrollToID: String?
    var isJobFilterFocused: FocusState<Bool>.Binding
    let reloadAllAction: () async -> Void
    let saveOrderAction: () -> Void
    

    var body: some View {
        VStack {
            if visibleStudios.isEmpty {
                Text("No studios enabled. Select a studio from the sidebar to begin.")
                    .foregroundColor(.secondary)
            } else {
                let columns = [GridItem(.adaptive(minimum: 300))]
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVGrid(columns: columns, spacing: 16) {
                            ForEach(visibleStudios) { studio in
                                if let viewModel = viewModels[studio.id] {
                                    let matchingJobs = viewModel.filteredJobs(filterText: filterText)
                                    if !hideEmpty || !matchingJobs.isEmpty {
                                        StudioColumnView(
                                            viewModel: viewModel,
                                            filterText: $filterText
                                        )
                                        .id(studio.id)
                                    }
                                }
                            }
                        }
                        .padding()
                    }
                    .onChange(of: scrollToID) { _, newValue in
                        if let id = newValue {
                            withAnimation {
                                proxy.scrollTo(id, anchor: .top)
                            }
                            // Reset state after scrolling
                            scrollToID = nil
                        }
                    }
                }
            }
        }
        .navigationTitle("Job Browser")
        .toolbar {
            ToolbarItemGroup {
                ClearableTextField(placeholder: "Filter job titles...", text: $filterText)
                    .frame(minWidth: 250)
                    .focused(isJobFilterFocused)
                
                Toggle("Hide Empty", isOn: $hideEmpty)
                    .help("Hide studios with no matching jobs")

                Button(action: {
                    Task { await reloadAllAction() }
                }) {
                    Label("Refresh All", systemImage: "arrow.clockwise")
                }
                .help("Refresh all visible job lists")
            }
        }
    }
}

struct ClearableTextField: View {
    var placeholder: String
    @Binding var text: String

    var body: some View {
        HStack {
            TextField(placeholder, text: $text)
                .textFieldStyle(.roundedBorder)
            
            if !text.isEmpty {
                Button(action: { self.text = "" }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

