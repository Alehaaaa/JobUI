import SwiftUI

// The main view for a single studio column.
struct StudioColumnView: View {
    @ObservedObject var viewModel: StudioViewModel
    @Binding var filterText: String

    private var filteredJobs: [Job] {
        if filterText.isEmpty {
            return viewModel.jobs
        }
        return viewModel.jobs.filter {
            $0.title.range(of: filterText, options: [.caseInsensitive, .diacriticInsensitive]) != nil
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Spacer()
                
                Link(destination: viewModel.studio.website) {
                    CachedAsyncImage(url: viewModel.studio.logoUrl) {
                        Text(viewModel.studio.name)
                            .font(.headline)
                    }
                }
                .frame(height: 40)
                
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
    }
}

