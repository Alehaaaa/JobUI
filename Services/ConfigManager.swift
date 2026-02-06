import Foundation

public class ConfigManager {
    public static let shared = ConfigManager()
    
    private let studiosFilename = "studios.json"
    private let lastCheckKey = "lastConfigUpdateCheck"
    private let etagKey = "configETag"
    private let lastModifiedKey = "configLastModified"
    
    private var applicationSupportDirectory: URL {
        let paths = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
        let appSupportDir = paths[0].appendingPathComponent("JobUI")
        if !FileManager.default.fileExists(atPath: appSupportDir.path) {
            try? FileManager.default.createDirectory(at: appSupportDir, withIntermediateDirectories: true)
        }
        return appSupportDir
    }
    
    public var studiosConfigURL: URL {
        return applicationSupportDirectory.appendingPathComponent(studiosFilename)
    }
    
    public func loadStudios() -> [Studio] {
        let fileManager = FileManager.default
        let decoder = JSONDecoder()
        var loadedStudios: [Studio] = []
        
        // 1. Try Application Support first
        if fileManager.fileExists(atPath: studiosConfigURL.path) {
            do {
                let data = try Data(contentsOf: studiosConfigURL)
                loadedStudios = try decoder.decode([Studio].self, from: data)
            } catch {
                print("Failed to load studios from App Support: \(error)")
                // If it failed due to corruption, we might want to delete it so the next check redownloads it
                try? fileManager.removeItem(at: studiosConfigURL)
            }
        }
        
        // 2. If nothing from App Support, try Bundle
        if loadedStudios.isEmpty, let bundleURL = Bundle.main.url(forResource: "studios", withExtension: "json") {
            do {
                let data = try Data(contentsOf: bundleURL)
                loadedStudios = try decoder.decode([Studio].self, from: data)
            } catch {
                print("Failed to load studios from Bundle: \(error)")
            }
        }
        
        // Handle sorting and deduplication
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
        
        return sortedStudios
    }
    
    public func updateConfigIfNeeded() async -> Bool {
        let commitApiUrl = URL(string: "https://api.github.com/repos/Alehaaaa/JobUI/commits?path=config/studios.json&per_page=1")!
        let rawContentUrl = URL(string: "https://raw.githubusercontent.com/Alehaaaa/JobUI/refs/heads/main/config/studios.json")!
        
        do {
            var request = URLRequest(url: commitApiUrl)
            request.setValue("JobUI-mac-Updater", forHTTPHeaderField: "User-Agent")
            
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                return false
            }
            
            let commits = try JSONSerialization.jsonObject(with: data) as? [[String: Any]]
            guard let latestCommit = commits?.first,
                  let commitData = latestCommit["commit"] as? [String: Any],
                  let committer = commitData["committer"] as? [String: Any],
                  let dateStr = committer["date"] as? String else {
                return false
            }
            
            let savedDate = UserDefaults.standard.string(forKey: lastModifiedKey)
            if savedDate == dateStr && FileManager.default.fileExists(atPath: studiosConfigURL.path) {
                return false // Already up to date
            }
            
            // Download new config
            var contentRequest = URLRequest(url: rawContentUrl)
            contentRequest.addValue("JobUI-mac-Updater", forHTTPHeaderField: "User-Agent")
            contentRequest.addValue("application/json, text/plain, */*", forHTTPHeaderField: "Accept")
            
            let (newData, _) = try await URLSession.shared.data(for: contentRequest)
            try newData.write(to: studiosConfigURL)
            
            UserDefaults.standard.set(dateStr, forKey: lastModifiedKey)
            UserDefaults.standard.set(Date(), forKey: lastCheckKey)
            
            return true
        } catch {
            print("Failed to update config: \(error)")
            return false
        }
    }
    
    public func updateDatabase() async -> (success: Bool, message: String) {
        let rawContentUrl = URL(string: "https://raw.githubusercontent.com/Alehaaaa/JobUI/refs/heads/main/config/studios.json")!
        
        do {
            // Download new config
            let (newData, _) = try await URLSession.shared.data(from: rawContentUrl)
            let decoder = JSONDecoder()
            let newStudios = try decoder.decode([Studio].self, from: newData)
            
            // Load current studios
            let currentStudios = loadStudios()
            
            // Compare and merge
            var studiosDict = Dictionary(uniqueKeysWithValues: currentStudios.map { ($0.id, $0) })
            var addedCount = 0
            var updatedCount = 0
            
            for newStudio in newStudios {
                if studiosDict[newStudio.id] == nil {
                    addedCount += 1
                }
                studiosDict[newStudio.id] = newStudio
            }
            
            updatedCount = newStudios.count - addedCount
            
            // Save merged config
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let mergedData = try encoder.encode(Array(studiosDict.values))
            try mergedData.write(to: studiosConfigURL)
            
            UserDefaults.standard.set(Date(), forKey: lastCheckKey)
            
            let message: String
            if addedCount > 0 && updatedCount > 0 {
                message = "Database updated! Added \(addedCount) new studio(s), updated \(updatedCount) existing."
            } else if addedCount > 0 {
                message = "Database updated! Added \(addedCount) new studio(s)."
            } else if updatedCount > 0 {
                message = "Database updated! Refreshed \(updatedCount) studio(s)."
            } else {
                message = "Database is already up to date."
            }
            
            return (true, message)
        } catch {
            print("Failed to update database: \(error)")
            return (false, "Failed to update database: \(error.localizedDescription)")
        }
    }
}
