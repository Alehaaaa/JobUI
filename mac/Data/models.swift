import Foundation

// Represents a single job posting
public struct Job: Identifiable, Hashable, Equatable {
    public let id = UUID()
    public let title: String
    public let link: URL
    public let location: String?

    public init(title: String, link: URL, location: String?) {
        self.title = title
        self.link = link
        self.location = location
    }

    public static func == (lhs: Job, rhs: Job) -> Bool {
        return lhs.id == rhs.id && lhs.title == rhs.title && lhs.link == rhs.link && lhs.location == rhs.location
    }
}

// Represents a studio, decoded from the JSON file
public struct Studio: Identifiable, Codable, Hashable, Equatable {
    public let id: String
    public let name: String
    public let logoUrl: URL
    public let careersUrl: URL
    public let website: URL
    public let scrapingStrategy: String

    public enum CodingKeys: String, CodingKey {
        case id, name, logoUrl = "logo_url", careersUrl = "careers_url", website, scrapingStrategy = "scraping_strategy"
    }
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        logoUrl = try container.decode(URL.self, forKey: .logoUrl)
        careersUrl = try container.decode(URL.self, forKey: .careersUrl)
        website = try container.decodeIfPresent(URL.self, forKey: .website) ?? careersUrl
        scrapingStrategy = try container.decode(String.self, forKey: .scrapingStrategy)
    }

    public static func == (lhs: Studio, rhs: Studio) -> Bool {
        return lhs.id == rhs.id
    }
}
