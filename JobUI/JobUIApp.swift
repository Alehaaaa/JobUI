//
//  JobUIApp.swift
//  JobUI
//
//  Created by Alejandro Martín on 11/7/25.
//

// Liquid Glass backgrounds are applied in main views for macOS 18+ compatibility.

import SwiftUI

@main
struct JobUIApp: App {
    @StateObject private var appState = AppState()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
        .commands {
            // Remove default File menu
            CommandGroup(replacing: .newItem) { }
            
            // Remove default Edit menu
            CommandGroup(replacing: .pasteboard) { }
            CommandGroup(replacing: .undoRedo) { }
            CommandGroup(replacing: .textEditing) { }
            
            // Help Menu
            CommandGroup(replacing: .help) {
                Button("Update Database") {
                    Task {
                        await appState.updateDatabase()
                    }
                }
                .keyboardShortcut("U", modifiers: [.command])
                
                Button("Refetch All Logos") {
                    appState.showLogoRefreshAlert = true
                }
                .keyboardShortcut("R", modifiers: [.command, .shift])
                
                Divider()
                
                Button("About JobUI") {
                    appState.showAbout = true
                }
                .keyboardShortcut("/", modifiers: [.command])
            }
        }
    }
}

// MARK: - App State
@MainActor
class AppState: ObservableObject {
    @Published var studios: [Studio] = []
    @Published var disabledStudioIDs: Set<String> = []
    @Published var showAbout = false
    @Published var isRefetchingLogos = false
    @Published var isUpdatingDatabase = false
    @Published var updateMessage: String?
    @Published var showUpdateAlert = false
    @Published var showLogoRefreshAlert = false
    
    init() {
        loadStudios()
    }
    
    private func loadStudios() {
        self.studios = ConfigManager.shared.loadStudios()
        if let savedIDs = UserDefaults.standard.stringArray(forKey: "disabledStudioIDs") {
            self.disabledStudioIDs = Set(savedIDs)
        }
    }
    
    func updateDatabase() async {
        isUpdatingDatabase = true
        let result = await ConfigManager.shared.updateDatabase()
        isUpdatingDatabase = false
        
        updateMessage = result.message
        showUpdateAlert = true
        
        if result.success {
            // Reload studios after successful update
            loadStudios()
        }
    }
    
    func refetchAllLogos() async {
        isRefetchingLogos = true
        await ImageCache.shared.clearAllCachedImages()
        // Ensure UI transitions to loading state before clearing cache
        try? await Task.sleep(nanoseconds: 50_000_000)
        isRefetchingLogos = false
        // Reload studios just in case
        loadStudios()
    }
}
