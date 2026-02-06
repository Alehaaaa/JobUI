import Foundation
import AppKit
import SwiftSoup

public class JobScraper {
    public static let shared = JobScraper()

    public func fetchJobs(for studio: Studio, startingAt: Int = 1) async throws -> (jobs: [Job], total: Int) {
        guard let scraping = studio.scraping else {
            throw URLError(.unsupportedURL)
        }
        
        let jobsList = try await withThrowingTaskGroup(of: [Job].self) { group in
            for url in studio.careersUrl {
                group.addTask {
                    switch scraping.strategy {
                    case "json":
                        return try await self.fetchJSON(for: studio, from: url)
                    case "html":
                        return try await self.fetchHTML(for: studio, from: url)
                    case "json_text":
                        return try await self.fetchJSONText(for: studio, from: url)
                    case "rss":
                        return try await self.fetchRSS(for: studio, from: url)
                    default:
                        throw URLError(.unsupportedURL)
                    }
                }
            }
            
            var collected: [Job] = []
            var seenLinks = Set<String>()
            
            while let jobs = try await group.next() {
                for job in jobs {
                    let linkString = job.link.absoluteString.lowercased()
                    if !seenLinks.contains(linkString) {
                        collected.append(job)
                        seenLinks.insert(linkString)
                    }
                }
            }
            return collected
        }
        
        return (jobsList.sorted(by: { $0.title < $1.title }), jobsList.count)
    }

    // MARK: - Generic Scrapers
    
    private func fetchJSON(for studio: Studio, from url: URL) async throws -> [Job] {
        guard let scraping = studio.scraping else { return [] }
        
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        if let params = scraping.params {
            components.queryItems = params.flatMap { (key, value) -> [URLQueryItem] in
                if case .array(let items) = value {
                    return items.map { URLQueryItem(name: key, value: $0.stringValue) }
                }
                return [URLQueryItem(name: key, value: value.stringValue)]
            }
        }
        
        var request = URLRequest(url: components.url!)
        request.httpMethod = scraping.method ?? "GET"
        
        if let headers = scraping.headers {
            for (key, value) in headers {
                request.setValue(value, forHTTPHeaderField: key)
            }
        }
        
        if let payload = scraping.payload {
            let encoder = JSONEncoder()
            request.httpBody = try encoder.encode(payload)
            if request.value(forHTTPHeaderField: "Content-Type") == nil {
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            }
        } else if let formData = scraping.formData {
            let bodyString = formData.map { "\($0.key)=\($0.value.stringValue.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")" }.joined(separator: "&")
            request.httpBody = bodyString.data(using: .utf8)
            request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        }
        
        request.setValue("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36", forHTTPHeaderField: "User-Agent")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        let json = try JSONSerialization.jsonObject(with: data)
        
        return try await parseJSONItems(json, for: studio, from: url)
    }
    
    private func parseJSONItems(_ json: Any, for studio: Studio, from url: URL) async throws -> [Job] {
        guard let scraping = studio.scraping else { return [] }
        let mapping = scraping.map ?? [:]
        
        var items = extractJSON(json, path: scraping.path ?? "")
        if !(items is [[String: Any]]) && !(items is [Any]) {
            if let single = items as? [String: Any] {
                items = [single]
            } else {
                return []
            }
        }
        
        var itemArray: [[String: Any]] = []
        if let directArray = items as? [[String: Any]] {
            itemArray = directArray
        } else if let anyArray = items as? [Any] {
            itemArray = anyArray.compactMap { $0 as? [String: Any] }
        } else {
            return []
        }
        
        // Filter
        if let filter = scraping.filter {
            itemArray = itemArray.filter { item in
                let val = String(describing: extractJSON(item, path: filter.key) ?? "")
                return val.lowercased().hasPrefix(filter.startswith.lowercased())
            }
        }
        
        var jobs: [Job] = []
        for item in itemArray {
            let title = applyMapping(to: "title", item: item, mapping: mapping, rootURL: url)
            let linkStr = applyMapping(to: "link", item: item, mapping: mapping, rootURL: url)
            let location = applyMapping(to: "location", item: item, mapping: mapping, rootURL: url)
            let extraLinkStr = applyMapping(to: "extra_link", item: item, mapping: mapping, rootURL: url)
            
            if let job = processJob(title: title, linkStr: linkStr, location: location, extraLinkStr: extraLinkStr, studio: studio, url: url, mapping: mapping) {
                jobs.append(job)
            }
        }
        
        return jobs
    }
    
    private func fetchJSONText(for studio: Studio, from url: URL) async throws -> [Job] {
        guard let scraping = studio.scraping else { return [] }
        let htmlResponse = try await fetchHTMLContent(from: url, method: scraping.method ?? "GET", payload: scraping.payload, headers: scraping.headers)
        let doc = try SwiftSoup.parse(htmlResponse)
        
        let regex: String
        if let customRegex = scraping.jsonText?.regex {
            regex = customRegex
        } else if let varName = scraping.jsonText?.variable {
            regex = "(?:const|var|let)\\s+\(varName)\\s*=\\s*(\\[.*\\])\\s*;?"
        } else {
            regex = "const jobsData\\s*=\\s*(\\[.*\\])\\s*;?"
        }
        
        var text = ""
        // 1. Try script tags first
        if let scripts = try? doc.select(normalizeSelector(scraping.container ?? "script")) {
            let nsRegex = try? NSRegularExpression(pattern: regex, options: [.dotMatchesLineSeparators])
            for s in scripts {
                let contents = s.data()
                if !contents.isEmpty {
                    let nsRange = NSRange(contents.startIndex..., in: contents)
                    if let _ = nsRegex?.firstMatch(in: contents, range: nsRange) {
                        text = contents
                        break
                    }
                }
            }
        }
        
        // 2. Fallback: Search the entire raw HTML response
        if text.isEmpty {
            let nsRegex = try? NSRegularExpression(pattern: regex, options: [.dotMatchesLineSeparators])
            let nsRange = NSRange(htmlResponse.startIndex..., in: htmlResponse)
            if let _ = nsRegex?.firstMatch(in: htmlResponse, range: nsRange) {
                text = htmlResponse
            }
        }
        
        if !text.isEmpty {
            if let nsRegex = try? NSRegularExpression(pattern: regex, options: [.dotMatchesLineSeparators]) {
                let nsRange = NSRange(text.startIndex..., in: text)
                if let firstMatch = nsRegex.firstMatch(in: text, range: nsRange),
                   firstMatch.numberOfRanges > 1 {
                    let groupRange = firstMatch.range(at: 1)
                    if let r = Range(groupRange, in: text) {
                        let jsonStr = String(text[r])
                        if let jsonData = jsonStr.data(using: .utf8),
                           let json = try? JSONSerialization.jsonObject(with: jsonData) {
                            return try await parseJSONItems(json, for: studio, from: url)
                        }
                    }
                }
            }
        }
        return []
    }
    
    private func fetchHTML(for studio: Studio, from url: URL) async throws -> [Job] {
        guard let scraping = studio.scraping else { return [] }
        let mapping = scraping.map ?? [:]
        
        let htmlResponse = try await fetchHTMLContent(from: url, method: scraping.method ?? "GET", payload: scraping.payload, headers: scraping.headers)
        let doc = try SwiftSoup.parse(htmlResponse)
        
        guard let containerSelector = scraping.container else { return [] }
        let items = try doc.select(normalizeSelector(containerSelector))
        
        var jobs: [Job] = []
        for item in items {
            let title = applyMappingHTML(to: "title", element: item, mapping: mapping, rootURL: url)
            let linkStr = applyMappingHTML(to: "link", element: item, mapping: mapping, rootURL: url, defaultAttr: "href")
            let location = applyMappingHTML(to: "location", element: item, mapping: mapping, rootURL: url)
            let extraLinkStr = applyMappingHTML(to: "extra_link", element: item, mapping: mapping, rootURL: url, defaultAttr: "html")
            
            if let job = processJob(title: title, linkStr: linkStr, location: location, extraLinkStr: extraLinkStr, studio: studio, url: url, mapping: mapping, element: item) {
                jobs.append(job)
            }
        }
        
        return jobs
    }
    
    private func fetchRSS(for studio: Studio, from url: URL) async throws -> [Job] {
        guard let scraping = studio.scraping else { return [] }
        let mapping = scraping.map ?? [:]
        
        let xmlResponse = try await fetchHTMLContent(from: url)
        let doc = try SwiftSoup.parse(xmlResponse, "", Parser.xmlParser())
        
        let containerSelector = scraping.container ?? "item"
        let items = try doc.select(containerSelector)
        
        var jobs: [Job] = []
        for item in items {
            let title = applyMappingRSS(to: "title", element: item, mapping: mapping, rootURL: url, defaultTag: "title")
            let linkStr = applyMappingRSS(to: "link", element: item, mapping: mapping, rootURL: url, defaultTag: "link")
            let location = applyMappingRSS(to: "location", element: item, mapping: mapping, rootURL: url, defaultTag: "description")
            
            if let job = processJob(title: title, linkStr: linkStr, location: location, extraLinkStr: "", studio: studio, url: url, mapping: mapping) {
                jobs.append(job)
            }
        }
        
        return jobs
    }
    
    private func processJob(title: String, linkStr: String, location: String, extraLinkStr: String, studio: Studio, url: URL, mapping: [String: ScrapingMapValue], element: Element? = nil) -> Job? {
        var cleanedTitle = cleanText(title)
        let cleanedLocation = cleanText(location)
        
        if mapping["remove_location_from_title"]?.removeLocationFromTitle == true || mapping["title"]?.removeLocationFromTitle == true {
            cleanedTitle = cleanText(removeLocationFromTitle(title: cleanedTitle, location: cleanedLocation))
        }
        
        // Strategy-specific fallbacks
        if cleanedTitle.isEmpty, let element = element, studio.scraping?.container?.contains("h2") == true {
            cleanedTitle = cleanText((try? element.text()) ?? "")
        }
        
        if cleanedTitle.isEmpty || ["view job", "details", "read more", "apply", "careers", "unknown"].contains(cleanedTitle.lowercased()) {
            return nil
        }
        
        let link: URL
        if linkStr.isEmpty {
            link = (studio.website ?? url).absoluteURL
        } else if let l = URL(string: linkStr, relativeTo: studio.website ?? url) {
            link = l.absoluteURL
        } else {
            return nil
        }
        
        var extraLink: URL? = nil
        if !extraLinkStr.isEmpty {
            if let extraCfg = mapping["extra_link"], let regex = extraCfg.regexLink {
                if let nsRegex = try? NSRegularExpression(pattern: regex) {
                    let nsRange = NSRange(extraLinkStr.startIndex..., in: extraLinkStr)
                    if let firstMatch = nsRegex.firstMatch(in: extraLinkStr, range: nsRange) {
                        let matchRange = firstMatch.range(at: firstMatch.numberOfRanges > 1 ? 1 : 0)
                        if let r = Range(matchRange, in: extraLinkStr) {
                            extraLink = URL(string: String(extraLinkStr[r]), relativeTo: studio.website ?? url)
                        }
                    }
                }
            } else {
                extraLink = URL(string: extraLinkStr, relativeTo: studio.website ?? url)
            }
        }
        
        return Job(title: cleanedTitle, link: link, location: cleanedLocation.isEmpty ? nil : cleanedLocation, extraLink: extraLink?.absoluteURL)
    }

    // MARK: - Utilities
    
    private func extractJSON(_ data: Any, path: String) -> Any? {
        if path.isEmpty { return data }
        
        // Support fallback paths
        if path.contains(",") {
            let paths = path.components(separatedBy: ",").map { $0.trimmingCharacters(in: .whitespaces) }
            for p in paths {
                if let val = extractJSON(data, path: p), !(val is NSNull) {
                    if let s = val as? String, s.isEmpty { continue }
                    return val
                }
            }
            return nil
        }
        
        let parts = path.components(separatedBy: ".")
        var current: Any? = data
        
        for part in parts {
            var key = part
            var index: Int? = nil
            
            if part.contains("[") && part.contains("]") {
                let bits = part.components(separatedBy: "[")
                key = bits[0]
                let indexBit = bits[1].replacingOccurrences(of: "]", with: "")
                if indexBit == "*" {
                    // Wildcard handle
                    if let dict = current as? [String: Any], let next = dict[key] as? [Any] {
                        return next // Return the whole array
                    } else if let array = current as? [Any] {
                        return array
                    }
                } else {
                    index = Int(indexBit)
                }
            }
            
            if !key.isEmpty {
                if let dict = current as? [String: Any] {
                    current = dict[key]
                } else {
                    return nil
                }
            }
            
            if let idx = index, let array = current as? [Any] {
                if idx >= 0 && idx < array.count {
                    current = array[idx]
                } else {
                    return nil
                }
            }
        }
        
        return current
    }

    private func applyMapping(to field: String, item: [String: Any], mapping: [String: ScrapingMapValue], rootURL: URL) -> String {
        guard let mapValue = mapping[field] else { return "" }
        
        var val: String = ""
        if mapValue.source == "url" {
            val = rootURL.absoluteString
        } else if let path = mapValue.path {
            val = String(describing: extractJSON(item, path: path) ?? "")
        }
        
        return finalizeValue(val, config: mapValue)
    }
    
    private func applyMappingHTML(to field: String, element: Element, mapping: [String: ScrapingMapValue], rootURL: URL, defaultAttr: String = "text") -> String {
        guard let mapValue = mapping[field] else { return "" }
        
        var result = ""
        
        if mapValue.source == "url" {
            result = rootURL.absoluteString
        } else if let findPrevious = mapValue.findPrevious {
            // Traverse previous siblings and ancestors' previous siblings to find the matching element
            var found = false
            var current: Element? = element
            
            while let currentElement = current {
                var sibling = currentElement
                while let prev = try? sibling.previousElementSibling() {
                    // Check if this element matches the selector
                    if let matched = try? prev.select(normalizeSelector(findPrevious)).first() {
                        result = (try? matched.text()) ?? ""
                        found = true
                        break
                    }
                    // Also check if the element itself matches
                    if prev.tagName().lowercased() == findPrevious.lowercased() {
                        result = (try? prev.text()) ?? ""
                        found = true
                        break
                    }
                    sibling = prev
                }
                if found { break }
                current = currentElement.parent()
            }
        } else {
            let selector = mapValue.selector ?? ""
            let attr = mapValue.attr ?? defaultAttr
            
            do {
                let target: Element? = selector.isEmpty ? element : try element.select(normalizeSelector(selector)).first()
                if let target = target {
                    if attr == "text" {
                        result = try target.text()
                    } else if attr == "html" {
                        result = try target.outerHtml()
                    } else {
                        result = try target.attr(attr)
                    }
                }
            } catch {
                print("HTML extraction error for \(field): \(error)")
            }
        }
        
        return finalizeValue(result, config: mapValue)
    }
    
    private func applyMappingRSS(to field: String, element: Element, mapping: [String: ScrapingMapValue], rootURL: URL, defaultTag: String) -> String {
        guard let mapValue = mapping[field] else {
            return (try? element.select(defaultTag).first()?.text()) ?? ""
        }
        
        var result = ""
        if mapValue.source == "url" {
            result = rootURL.absoluteString
        } else {
            let selector = mapValue.selector ?? mapValue.path ?? defaultTag
            let attr = mapValue.attr ?? "text"
            
            do {
                if let target = try element.select(normalizeSelector(selector)).first() {
                    if attr == "text" {
                        result = try target.text()
                    } else {
                        result = try target.attr(attr)
                    }
                }
            } catch { }
        }
        
        return finalizeValue(result, config: mapValue)
    }
    
    private func finalizeValue(_ input: String, config: ScrapingMapValue) -> String {
        var val = input
        
        if let split = config.split {
            let parts = val.components(separatedBy: split.sep)
            if split.index >= 0 && split.index < parts.count {
                val = parts[split.index].trimmingCharacters(in: .whitespaces)
            }
        }
        
        if let regex = config.regex {
            if let range = val.range(of: regex, options: .regularExpression) {
                val = String(val[range])
                // Attempt to get first group if any
                if let nsRegex = try? NSRegularExpression(pattern: regex) {
                    let nsRange = NSRange(val.startIndex..., in: val)
                    if let firstMatch = nsRegex.firstMatch(in: val, range: nsRange), firstMatch.numberOfRanges > 1 {
                        let groupRange = firstMatch.range(at: 1)
                        if let r = Range(groupRange, in: val) {
                            val = String(val[r])
                        }
                    }
                }
            } else {
                val = ""
            }
        }
        
        if !val.isEmpty {
            if let prefix = config.prefix { val = prefix + val }
            if let suffix = config.suffix { val = val + suffix }
        }
        
        return val
    }

    private func fetchHTMLContent(from url: URL, method: String = "GET", payload: [String: JSONValue]? = nil, headers: [String: String]? = nil) async throws -> String {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.addValue("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36", forHTTPHeaderField: "User-Agent")
        
        if let headers = headers {
            for (key, value) in headers {
                request.setValue(value, forHTTPHeaderField: key)
            }
        }
        
        if let payload = payload {
            let encoder = JSONEncoder()
            request.httpBody = try encoder.encode(payload)
        }
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return String(data: data, encoding: .utf8) ?? ""
    }

    private func normalizeSelector(_ selector: String) -> String {
        guard !selector.isEmpty else { return selector }
        // Escape colons in CSS selectors for SwiftSoup compatibility
        return selector.replacingOccurrences(of: "\\\\", with: "\\")
    }

    private func removeLocationFromTitle(title: String, location: String?) -> String {
        guard let location = location, !location.isEmpty, !title.isEmpty else { return title }
        
        var result = title
        
        // 1. Basic removal of the full location string
        let escapedLocation = NSRegularExpression.escapedPattern(for: location)
        if let regex = try? NSRegularExpression(pattern: escapedLocation, options: .caseInsensitive) {
            result = regex.stringByReplacingMatches(in: result, range: NSRange(result.startIndex..., in: result), withTemplate: "")
        }
        
        // 2. Comma separated components
        if location.contains(",") {
            let parts = location.components(separatedBy: ",")
            for p in parts {
                let pStrip = p.trimmingCharacters(in: .whitespaces)
                if !pStrip.isEmpty {
                    let escapedPart = NSRegularExpression.escapedPattern(for: pStrip)
                    if let regex = try? NSRegularExpression(pattern: "\\b" + escapedPart + "\\b", options: .caseInsensitive) {
                        result = regex.stringByReplacingMatches(in: result, range: NSRange(result.startIndex..., in: result), withTemplate: "")
                    }
                }
            }
        }
        
        // 3. Collapse multiple separators
        if let regex = try? NSRegularExpression(pattern: "\\s*([ \\-\\|/\\\\·•])\\s*([ \\-\\|/\\\\·•]\\s*)+") {
            result = regex.stringByReplacingMatches(in: result, range: NSRange(result.startIndex..., in: result), withTemplate: " $1 ")
        }
        
        // 4. Remove empty brackets
        if let regex = try? NSRegularExpression(pattern: "\\(\\s*\\)|\\[\\s*\\]|\\{\\s*\\}") {
            result = regex.stringByReplacingMatches(in: result, range: NSRange(result.startIndex..., in: result), withTemplate: "")
        }
        
        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func cleanText(_ text: String) -> String {
        guard !text.isEmpty else { return "" }
        // Use SwiftSoup for reliable entity decoding and tag stripping
        let cleaned = (try? SwiftSoup.parse(text).text()) ?? text
        return cleaned.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "·•| -:"))
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
