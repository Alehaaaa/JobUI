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
        // Only show load more if the scraper supports it and we haven't loaded everything.
        studio.scrapingStrategy == "netflix_json" && jobs.count < totalJobs
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
}

// MARK: - Main Content View
struct ContentView: View {
    @State private var studios: [Studio] = []
    @State private var filterText = ""
    @State private var studioSearchText = ""
    @State private var disabledStudioIDs: Set<String> = []
    @State private var navigationVisibility = NavigationSplitViewVisibility.all
    @State private var viewModels: [String: StudioViewModel] = [:]
    
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

    var body: some View {
        NavigationSplitView(columnVisibility: $navigationVisibility) {
            // --- Sidebar ---
            VStack {
                ClearableTextField(placeholder: "Search studios...", text: $studioSearchText)
                    .padding([.horizontal, .top])

                List {
                    ForEach(filteredStudios) { studio in
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
                                Text(studio.name).font(.headline)
                            }
                        }
                        .listRowBackground(Color.clear)
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

        } detail: {
            StudioGridView(
                studios: $studios,
                visibleStudios: visibleStudios,
                viewModels: viewModels,
                filterText: $filterText,
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
    }

    // MARK: Data Helpers
    private func loadData() {
        loadStudios()
        loadDisabledStudios()
        updateViewModels()
    }

    private func loadStudios() {
        guard let url = Bundle.main.url(forResource: "studios", withExtension: "json") else {
            print("studios.json not found")
            return
        }
        do {
            let loadedStudios = try JSONDecoder().decode([Studio].self, from: try Data(contentsOf: url))
            let savedOrder = UserDefaults.standard.stringArray(forKey: "studioOrder") ?? []
            
            var seen = Set<String>()
            let studioDict = Dictionary(uniqueKeysWithValues: loadedStudios.map { ($0.id, $0) })
            
            var sortedStudios = savedOrder.compactMap { id -> Studio? in
                if seen.contains(id) { return nil }
                seen.insert(id)
                return studioDict[id]
            }
            
            for studio in loadedStudios {
                if !seen.contains(studio.id) {
                    sortedStudios.append(studio)
                }
            }
            
            self.studios = sortedStudios
            
        } catch {
            print("Failed to load or parse studios.json: \(error)")
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
                ScrollView {
                    LazyVGrid(columns: columns, spacing: 16) {
                        ForEach(visibleStudios) { studio in
                            if let viewModel = viewModels[studio.id] {
                                StudioColumnView(
                                    viewModel: viewModel,
                                    filterText: $filterText
                                )
                            }
                        }
                    }
                    .padding()
                }
            }
        }
        .navigationTitle("Job Browser")
        .toolbar {
            ToolbarItemGroup {
                ClearableTextField(placeholder: "Filter job titles...", text: $filterText)
                    .frame(minWidth: 250)
                    .focused(isJobFilterFocused)

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

