import SwiftUI

struct JobListView: View {
    let jobs: [Job]
    let studioName: String

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if jobs.isEmpty {
                Text("No job opportunities found.")
                    .foregroundColor(.secondary)
                    .padding()
            } else {
                List(jobs) { job in
                    Link(destination: job.link) {
                        Text(job.title)
                            .padding(.vertical, 4)
                    }
                }
            }
        }
        .navigationTitle("\(studioName) Jobs")
    }
}
