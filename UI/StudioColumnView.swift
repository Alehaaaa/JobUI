import SwiftUI

// The main view for a single studio column.
struct StudioColumnView: View {
    @EnvironmentObject var appState: AppState
    @ObservedObject var viewModel: StudioViewModel
    @Binding var filterText: String
    @State private var isRefreshingLogo = false

    private var filteredJobs: [Job] {
        viewModel.filteredJobs(filterText: filterText)
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Spacer()
                
                Link(destination: viewModel.studio.website ?? viewModel.studio.careersUrl.first!) {
                    if isRefreshingLogo || appState.isRefetchingLogos {
                        ProgressView()
                            .frame(height: 40)
                    } else {
                        CachedAsyncImage(url: viewModel.studio.logoUrl, studioId: viewModel.studio.id) {
                            Text(viewModel.studio.name)
                                .font(.headline)
                        }
                    }
                }
                .frame(height: 40)
                .contextMenu {
                    Button("Refresh Logo") {
                        Task {
                            isRefreshingLogo = true
                            await ImageCache.shared.clearCachedImage(studioId: viewModel.studio.id)
                            // Small delay to ensure cache is cleared
                            try? await Task.sleep(nanoseconds: 100_000_000)
                            isRefreshingLogo = false
                        }
                    }
                    Button("Open Careers Page") {
                        if let url = viewModel.studio.website ?? viewModel.studio.careersUrl.first {
                            NSWorkspace.shared.open(url)
                        }
                    }
                }
                
                Spacer()
                
                Button(action: { Task { await viewModel.fetchJobs(isRefresh: true) } }) {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(.borderless)
            }
            .padding()
            .background(Material.ultraThinMaterial)


            Divider()

            // Content
            Group {
                if viewModel.isLoading {
                    ProgressView().frame(maxHeight: .infinity)
                } else if let errorMessage = viewModel.errorMessage {
                    VStack {
                        Text("Error").font(.headline)
                        Text(errorMessage).foregroundColor(.red)
                        Spacer()
                    }.padding()
                } else if filteredJobs.isEmpty {
                    VStack {
                        Text("No jobs found").foregroundColor(.secondary)
                        if !filterText.isEmpty {
                            Text("for '\(filterText)'").foregroundColor(.secondary)
                        }
                        Spacer()
                    }.padding()
                } else {
                    List {
                        ForEach(filteredJobs) { job in
                            JobRowView(job: job)
                                .onAppear {
                                    // Trigger next page load when the last item appears
                                    if filterText.isEmpty && job.id == filteredJobs.last?.id {
                                        Task {
                                            await viewModel.fetchJobs(isRefresh: false)
                                        }
                                    }
                                }
                        }
                        
                        // Show the loading wheel only when fetching more pages
                        if viewModel.isLoadingMore {
                            HStack {
                                Spacer()
                                ProgressView()
                                Spacer()
                            }
                        }
                    }
                    .listStyle(.plain)
                }
            }
        }
        .frame(minWidth: 250, idealWidth: 300, maxWidth: .infinity, minHeight: 400)
        .onAppear {
            if viewModel.jobs.isEmpty {
                Task {
                    await viewModel.fetchJobs(isRefresh: true)
                }
            }
        }
        .background(Material.ultraThinMaterial)
        .cornerRadius(10)
        .shadow(radius: 2)
        .onChange(of: filteredJobs) {} // Optimization to re-render only when jobs change
    }
}

struct JobRowView: View {
    let job: Job
    
    var body: some View {
        HStack {
            Link(destination: job.link) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(job.title).font(.headline)
                    if let location = job.location, !location.isEmpty {
                        Text(location).font(.subheadline).foregroundColor(.secondary)
                    }
                }
                .padding(.vertical, 4)
            }
            .buttonStyle(.plain)
            
            if let extraLink = job.extraLink {
                Spacer()
                Link(destination: extraLink) {
                    Image(systemName: "doc.text.fill")
                        .foregroundColor(.blue)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

