import Foundation
import AppKit
import SwiftSoup

public class JobScraper {
    public static let shared = JobScraper()

        public func fetchJobs(for studio: Studio, startingAt: Int = 1) async throws -> (jobs: [Job], total: Int) {
        switch studio.scrapingStrategy {
        case "netflix_json":
            return try await self.fetchNetflixJobs(from: studio, startingAt: startingAt)
        // For other studios, we'll wrap the result in a tuple. They don't support pagination yet.
        case "workday_json":
            let jobs = try await self.fetchPixarJobs(from: studio)
            return (jobs, jobs.count)
        case "dreamworks_json":
            let jobs = try await self.fetchDreamworksJobs(from: studio)
            return (jobs, jobs.count)
        case "lever_json":
            let jobs = try await self.fetchLeverJobs(from: studio)
            return (jobs, jobs.count)
        case "bamboohr_json":
            let jobs = try await self.fetchBambooHRJobs(from: studio)
            return (jobs, jobs.count)
        case "smartrecruiters_json":
            let jobs = try await self.fetchSmartRecruitersJobs(from: studio)
            return (jobs, jobs.count)
        case "dneg_html":
            let jobs = try await self.fetchDnegJobs(from: studio)
            return (jobs, jobs.count)
        case "disney_html":
            let jobs = try await self.fetchDisneyJobs(from: studio)
            return (jobs, jobs.count)
        case "ranchito_html":
            let jobs = try await self.fetchRanchitoJobs(from: studio)
            return (jobs, jobs.count)
        case "greenhouse_html":
            let jobs = try await self.fetchGreenhouseJobs(from: studio)
            return (jobs, jobs.count)
        case "mikros_html":
            let jobs = try await self.fetchMikrosJobs(from: studio)
            return (jobs, jobs.count)
        case "fortiche_html":
            let jobs = try await self.fetchForticheJobs(from: studio)
            return (jobs, jobs.count)
        case "steamroller_html":
            let jobs = try await self.fetchSteamrollerJobs(from: studio)
            return (jobs, jobs.count)
        case "framestore_html":
            let jobs = try await self.fetchFramestoreJobs(from: studio)
            return (jobs, jobs.count)
        case "giant_html":
            let jobs = try await self.fetchGiantJobs(from: studio)
            return (jobs, jobs.count)
        case "skydance_html":
            let jobs = try await self.fetchSkydanceJobs(from: studio)
            return (jobs, jobs.count)
        case "illusorium_html":
            let jobs = try await self.fetchIllusoriumJobs(from: studio)
            return (jobs, jobs.count)
        default:
            throw URLError(.unsupportedURL)
        }
    }

    // MARK: - Scraper Implementations
    
    private func fetchNetflixJobs(from studio: Studio, startingAt: Int) async throws -> (jobs: [Job], total: Int) {
        struct JobPosting: Decodable {
            let name: String
            let canonicalPositionUrl: URL
            let location: String?
        }

        struct Response: Decodable {
            let positions: [JobPosting]
            let count: Int
        }

        let pageSize = 10 // Correct page size for Netflix API

        guard var components = URLComponents(url: studio.careersUrl, resolvingAgainstBaseURL: false) else {
            throw URLError(.badURL)
        }

        components.queryItems = [
            URLQueryItem(name: "domain", value: "netflix.com"),
            URLQueryItem(name: "start", value: String(startingAt)),
            URLQueryItem(name: "num", value: String(pageSize)),
            URLQueryItem(name: "sort_by", value: "relevance"),
            URLQueryItem(name: "Teams", value: "Animation"),
            URLQueryItem(name: "Teams", value: "Feature Animation - Art"),
            URLQueryItem(name: "Teams", value: "Feature Animation - Editorial + Post"),
            URLQueryItem(name: "Teams", value: "Feature Animation - Production Management"),
            URLQueryItem(name: "Teams", value: "Feature Animation - Story"),
            URLQueryItem(name: "Teams", value: "Feature Animation")
        ]

        guard let url = components.url else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(Response.self, from: data)
        
        let jobs = await response.positions.asyncMap {
            var location = $0.location
            if let loc = location {
                location = loc.components(separatedBy: ",").joined(separator: ", ")
            }
            let title = await $0.name.decodingHTMLEntities()
            return Job(title: title, link: $0.canonicalPositionUrl, location: location)
        }
        
        return (jobs, response.count)
    }
    
    private func fetchSkydanceJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        
        let sections = try doc.select("div[id^=skydance_animation].mb-60")
        var jobs: [Job] = []

        for section in sections {
            let jobElements = try section.select(".mb-40")
            for element in jobElements {
                guard
                    let titleElement = try element.select(".treatment-title-small").first(),
                    let linkElement = try element.select("a").first()
                else {
                    continue
                }

                let title = try titleElement.text()
                let linkPath = try linkElement.attr("href")
                let location = try element.select(".treatment-button").first()?.text()

                if let url = URL(string: linkPath, relativeTo: studio.website) {
                    jobs.append(Job(title: title, link: url.absoluteURL, location: location))
                }
            }
        }
        return jobs
    }

    private func fetchPixarJobs(from studio: Studio) async throws -> [Job] {
        struct JobPosting: Codable { let title: String; let externalPath: String }
        struct Response: Codable { let jobPostings: [JobPosting] }
        
        var request = URLRequest(url: studio.careersUrl)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let jsonBody = ["appliedFacets": [:], "limit": 20, "searchText": ""] as [String: Any]
        request.httpBody = try JSONSerialization.data(withJSONObject: jsonBody)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(Response.self, from: data)
        
        let jobs = await response.jobPostings.asyncMap {
            let title = await $0.title.decodingHTMLEntities()
            return Job(title: title, link: studio.website.appendingPathComponent($0.externalPath), location: nil)
        }
        return jobs
    }

    private func fetchDreamworksJobs(from studio: Studio) async throws -> [Job] {
        struct JobPosting: Codable { let title: String; let field_detailurl: URL; let field_location: String }
        struct ResponseData: Codable { let rows: [JobPosting] }
        
        let (data, _) = try await URLSession.shared.data(from: studio.careersUrl)
        let response = try JSONDecoder().decode([ResponseData].self, from: data)
        
        let jobs = await response.first?.rows.asyncMap {
            let title = await $0.title.decodingHTMLEntities()
            let location = await $0.field_location.decodingHTMLEntities()
            return Job(title: title, link: $0.field_detailurl, location: location)
        }
        return jobs ?? []
    }

    private func fetchDisneyJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobRows: Elements = try doc.select("tr:has(span.job-location)")
        
        return try jobRows.compactMap { row -> Job? in
            guard
                let titleElement = try row.select("h2").first(),
                let linkElement = try row.select("a").first(),
                let locationElement = try row.select("span.job-location").first()
            else {
                return nil
            }
            
            let title = try titleElement.text()
            let href = try linkElement.attr("href")
            let location = try locationElement.text()
            
            return Job(title: title, link: studio.website.appendingPathComponent(href), location: location)
        }
    }
    
    private func fetchRanchitoJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobElements: Elements = try doc.select("li:has(h5.post-date)")

        return try jobElements.compactMap { element -> Job? in
            guard
                let h2 = try element.select("h2").first(),
                let a = try element.select("a").first(),
                let h5 = try element.select("h5.post-date").first()
            else {
                return nil
            }

            let title = try h2.text()
            let link = try a.attr("href")
            let location = try h5.text()

            return Job(
                title: title,
                link: studio.website.appendingPathComponent(link),
                location: location
            )
        }
    }
    
    private func fetchDnegJobs(from studio: Studio) async throws -> [Job] {

        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobRows: Elements = try doc.select("li.mb1")

        return try jobRows.compactMap { row -> Job? in
            guard
                let titleElement = try row.select("p").first(),
                let linkElement = try row.select("a").first(),
                let locationElement = try row.select("div.jv-job-list-location").first()
            else {
                return nil
            }

            let title = try titleElement.text().trimmingCharacters(in: .whitespacesAndNewlines)
            let link = try linkElement.attr("href")
            let rawLocation = try locationElement.text()
            let location = rawLocation
                .components(separatedBy: .whitespacesAndNewlines)
                .filter { !$0.isEmpty }
                .joined(separator: " ")

            guard let url = URL(string: "https://jobs.jobvite.com\(link)") else {
                return nil
            }

            return Job(title: title, link: url, location: location)
        }
    }



    private func fetchGreenhouseJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobRows: Elements = try doc.select("tr.job-post")

        return try jobRows.compactMap { row -> Job? in
            guard
                let titleElement = try row.select("p").first(),
                let linkElement = try row.select("a").first(),
                let locationElement = try row.select("p.body__secondary").first()
            else {
                return nil
            }
            
            let title = try titleElement.text()
            let link = try linkElement.attr("href")
            let location = try locationElement.text()
            
            guard let url = URL(string: link) else { return nil }

            return Job(title: title, link: url, location: location)
        }
    }
    
    private func fetchLeverJobs(from studio: Studio) async throws -> [Job] {
        struct JobPosting: Decodable {
            let text: String
            let hostedUrl: URL
            let categories: Categories
            struct Categories: Decodable {
                let location: String?
            }
        }
        let (data, _) = try await URLSession.shared.data(from: studio.careersUrl)
        let postings = try JSONDecoder().decode([JobPosting].self, from: data)
        return await postings.asyncMap {
            let title = await $0.text.decodingHTMLEntities()
            return Job(title: title, link: $0.hostedUrl, location: $0.categories.location)
        }
    }

    private func fetchBambooHRJobs(from studio: Studio) async throws -> [Job] {
        struct JobPosting: Decodable {
            let id: String
            let jobOpeningName: String
            let location: Location?
            
            struct Location: Decodable {
                let city: String?
                let state: String?
            }
        }

        struct Response: Decodable {
            let result: [JobPosting]
        }

        guard let url = URL(string: "\(studio.careersUrl)/careers/list") else {
            throw URLError(.badURL)
        }
        let (data, _) = try await URLSession.shared.data(from: url)

        let response = try JSONDecoder().decode(Response.self, from: data)

        return await response.result.asyncMap {
            let city = $0.location?.city?.trimmingCharacters(in: .whitespacesAndNewlines)
            let state = $0.location?.state?.trimmingCharacters(in: .whitespacesAndNewlines)

            let location = [city, state].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
            let title = await $0.jobOpeningName.decodingHTMLEntities()

            return Job(
                title: title,
                link: studio.website.appendingPathComponent("careers/\($0.id)"),
                location: location
            )
        }
    }


    private func fetchSmartRecruitersJobs(from studio: Studio) async throws -> [Job] {
        struct JobPosting: Decodable {
            let name: String
            let id: String
            let location: Categories
            struct Categories: Decodable {
                let fullLocation: String?
            }
        }
        struct Response: Decodable { let content: [JobPosting] }
        let (data, _) = try await URLSession.shared.data(from: studio.careersUrl)
        let response = try JSONDecoder().decode(Response.self, from: data)
        return await response.content.asyncMap {
            let title = await $0.name.decodingHTMLEntities()
            return Job(title: title, link: studio.website.appendingPathComponent($0.id), location: $0.location.fullLocation)
        }
    }

    private func fetchMikrosJobs(from studio: Studio) async throws -> [Job] {
        // "https://www.mikrosanimation.com/wp-json/mikros/api/jobs/"
        // "https://www.mikrosanimation.com/en/people-and-culture/careers/"
        struct JobPosting: Decodable {
            let name: String
            let id: String
            let location: Categories
            struct Categories: Decodable {
                let fullLocation: String?
            }
            let department: House
            struct House: Decodable {
                let label: String?
            }
        }

        struct Response: Decodable {
            let content: [JobPosting]
        }

        let (data, _) = try await URLSession.shared.data(from: studio.careersUrl)
        let response = try JSONDecoder().decode(Response.self, from: data)

        let filteredJobs = response.content.filter {
            $0.department.label?.hasPrefix("Mikros Animation") == true
        }

        return await filteredJobs.asyncMap {
            let title = await $0.name.decodingHTMLEntities()
            return Job(
                title: title,
                link: studio.website.appendingPathComponent($0.id),
                location: $0.location.fullLocation
            )
        }
    }

/*        struct Response: Codable {
            let reportEntry: [JobData]
            enum CodingKeys: String, CodingKey { case reportEntry = "Report_Entry" }
        }
        struct JobData: Codable {
            let title: String, url: String, city: String, country: String
            enum CodingKeys: String, CodingKey { case title, url, city, country = "Country" }
        }

        let url = URL(string: "https://www.mikrosanimation.com/wp-json/mikros/api/jobs/")!
        let (data, _) = try await URLSession.shared.data(from: url)
        
        guard let jsonString = String(data: data, encoding: .utf8),
              jsonString.trimmingCharacters(in: .whitespacesAndNewlines) != "false",
              let innerJsonData = jsonString.data(using: .utf8) else {
            return []
        }

        let jobData: Response
        do {
            let innerJsonString = try JSONDecoder().decode(String.self, from: innerJsonData)
            guard let finalJsonData = innerJsonString.data(using: .utf8) else { return [] }
            jobData = try JSONDecoder().decode(Response.self, from: finalJsonData)
        } catch {
            jobData = try JSONDecoder().decode(Response.self, from: innerJsonData)
        }
        
        return jobData.reportEntry.compactMap { entry -> Job? in
            var city = entry.city
            if city.contains(",") {
                city = city.components(separatedBy: ",").map { $0.trimmingCharacters(in: .whitespaces) }.reversed().joined(separator: " ")
            }
            let location = "\(city), \(entry.country)"
            guard let url = URL(string: entry.url) else { return nil }
            return Job(title: entry.title, link: url, location: location)
        }
    } */

    private func fetchForticheJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobElements: Elements = try doc.select(".jet-engine-listing-overlay-wrap")

        return try jobElements.compactMap { element -> Job? in
            guard let titleElement = try element.select("h3").first() else { return nil }
            let title = try titleElement.text()
            let link = try element.attr("data-url")
            guard let url = URL(string: link) else { return nil }
            return Job(title: title, link: url, location: nil)
        }
    }

    private func fetchSteamrollerJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobElements: Elements = try doc.select("div.css-aapqz6")

        return try jobElements.compactMap { element -> Job? in
            guard
                let titleElement = try element.select("a[href]").first(),
                let locationElement = try element.select("span[data-icon=LOCATION_OUTLINE] + p").first()
            else {
                return nil
            }
            
            let title = try titleElement.text()
            let link = try titleElement.attr("href")
            let location = try locationElement.text()

            guard link.contains("/jobs/"), let url = URL(string: link, relativeTo: studio.website) else { return nil }

            return Job(title: title, link: url.absoluteURL, location: location)
        }
    }
    
    private func fetchIllusoriumJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)

        let rowContainers: Elements = try doc.select("div.row-container")
        var seenURLs = Set<String>()
        var jobs = [Job]()

        for container in rowContainers.array() {
            guard let btnContainer = try? container.select("span.btn-container").first(),
                  let linkElement = try? btnContainer.select("a[href]").first(),
                  let href = try? linkElement.attr("href"),
                  href.contains("/job_posting/"),
                  let jobURL = URL(string: href, relativeTo: studio.website)
            else {
                continue
            }

            if seenURLs.contains(href) {
                continue
            }
            seenURLs.insert(href)

            var title = try? container.select("div.uncode_text_column.text-lead h4").first()?.text()

            if title == nil {
                title = try? container.select("div.uncode_text_column.text-lead p").first()?.text()
            }

            let finalTitle = title ?? "Title not found"

            jobs.append(Job(title: finalTitle, link: jobURL.absoluteURL, location: ""))
        }

        return jobs
    }


    private func fetchFramestoreJobs(from studio: Studio) async throws -> [Job] {
        var request = URLRequest(url: studio.careersUrl)
        request.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")

        let (data, _) = try await URLSession.shared.data(for: request)
        guard let html = String(data: data, encoding: .utf8) else {
            throw NSError(domain: "FetchError", code: 1, userInfo: [NSLocalizedDescriptionKey: "Invalid HTML encoding"])
        }

        let doc = try SwiftSoup.parse(html)
        let jobRows = try doc.select("div").filter { div in
            let childAnchor = try div.select("> a[href^=/o/]").first()
            return childAnchor != nil
        }

        var seen = Set<String>()
        var jobs: [Job] = []

        for row in jobRows {
            guard let titleElement = try row.select("a[href^=/o/]").first() else { continue }

            let href = try titleElement.attr("href")
            if seen.contains(href) { continue }

            let title = try titleElement.text()
            if title.lowercased() == "view job" { continue }

            seen.insert(href)

            let cityElement = try row.select(".custom-css-style-job-location-city").first()
            let countryElement = try row.select(".custom-css-style-job-location-country").first()

            var location: String?
            if let city = try cityElement?.text(), let country = try countryElement?.text() {
                location = "\(city), \(country)"
            }

            guard let jobURL = URL(string: href, relativeTo: studio.careersUrl) else { continue }

            jobs.append(Job(title: title, link: jobURL, location: location))
        }

        return jobs
    }



    private func fetchGiantJobs(from studio: Studio) async throws -> [Job] {
        let html = try await fetchHTML(from: studio.careersUrl)
        let doc: Document = try SwiftSoup.parse(html)
        let jobElements: Elements = try doc.select(".g-careers .row .col-12")

        return try jobElements.compactMap { element -> Job? in
            guard
                let titleElement = try element.select("h4").first(),
                let locationElement = try element.select("span").first(),
                let linkElement = try element.select("a").first()
            else {
                return nil
            }
            
            let title = try titleElement.text()
            let location = try locationElement.text()
            let link = try linkElement.attr("href")
            
            guard let url = URL(string: link) else { return nil }

            return Job(title: title, link: url, location: location)
        }
    }

    // MARK: - Scraper Utilities

    private func fetchHTML(from url: URL) async throws -> String {
        var request = URLRequest(url: url)
        request.addValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        let (data, _) = try await URLSession.shared.data(for: request)
        return String(data: data, encoding: .utf8) ?? ""
    }

    private func decodeAndCleanHTML(_ text: String) async -> String {
        let decoded = await text.decodingHTMLEntities()
        let stripped = decoded.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
        return stripped.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

// MARK: - String Extension for HTML Decoding
extension String {
    @MainActor
    func decodingHTMLEntities() -> String {
        guard !self.isEmpty else { return self }
        guard let data = self.data(using: .utf8) else { return self }
        let options: [NSAttributedString.DocumentReadingOptionKey: Any] = [
            .documentType: NSAttributedString.DocumentType.html,
            .characterEncoding: String.Encoding.utf8.rawValue
        ]
        guard let attributedString = try? NSAttributedString(data: data, options: options, documentAttributes: nil) else {
            return self
        }
        return attributedString.string
    }
}

// MARK: - Collection Extension for Async Operations
extension Collection {
    func asyncMap<T>(_ transform: (Element) async throws -> T) async rethrows -> [T] {
        var result = [T]()
        for element in self {
            result.append(try await transform(element))
        }
        return result
    }
}
