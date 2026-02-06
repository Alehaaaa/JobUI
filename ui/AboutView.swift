import SwiftUI

struct AboutView: View {
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        VStack(spacing: 20) {
            // App Icon or Logo
            Image(systemName: "briefcase.fill")
                .font(.system(size: 60))
                .foregroundColor(.blue)
            
            Text("JobUI")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            if let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String {
                Text("Version \(version)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Divider()
                .padding(.horizontal, 40)
            
            VStack(spacing: 8) {
                Text("Created by @Alehaaaa")
                    .font(.body)
                
                Link("alehaaaa.github.io", destination: URL(string: "https://alehaaaa.github.io")!)
                    .font(.body)
                
                HStack(spacing: 16) {
                    Link("LinkedIn", destination: URL(string: "https://www.linkedin.com/in/alejandro-martin-407527215")!)
                    Text("•")
                        .foregroundColor(.secondary)
                    Link("Instagram", destination: URL(string: "https://www.instagram.com/alejandro_anim")!)
                }
                .font(.body)
            }
            
            Spacer()
                .frame(height: 20)
            
            Text("If you liked this tool, you can send me some love!")
                .multilineTextAlignment(.center)
                .font(.body)
                .foregroundColor(.secondary)
            
            Button("Close") {
                dismiss()
            }
            .keyboardShortcut(.defaultAction)
            .padding(.top, 10)
        }
        .padding(30)
        .frame(width: 400, height: 400)
    }
}

#Preview {
    AboutView()
}
