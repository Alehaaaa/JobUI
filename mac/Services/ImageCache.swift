import SwiftUI
import Combine
import Cocoa

@MainActor
class ImageCache: ObservableObject {
    static let shared = ImageCache()
    private let fileManager = FileManager.default
    private let cacheDirectory: URL

    private init() {
        let cachesURL = fileManager.urls(for: .cachesDirectory, in: .userDomainMask).first!
        cacheDirectory = cachesURL.appendingPathComponent("ImageCache")
        try? fileManager.createDirectory(at: cacheDirectory, withIntermediateDirectories: true, attributes: nil)
    }

    func loadImageData(for url: URL) async -> Data? {
        let fileURL = cacheDirectory.appendingPathComponent(url.lastPathComponent)
        
        // Check cache first
        if let data = try? Data(contentsOf: fileURL) {
            return data
        }

        // If not in cache, download
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            try data.write(to: fileURL)
            return data
        } catch {
            print("Failed to load image data from \(url): \(error)")
            return nil
        }
    }
}

struct CachedAsyncImage<Fallback: View>: View {
    let url: URL
    private let fallback: () -> Fallback
    @State private var image: NSImage?
    @State private var hasError = false

    init(url: URL, @ViewBuilder fallback: @escaping () -> Fallback) {
        self.url = url
        self.fallback = fallback
    }

    var body: some View {
        Group {
            if let image = image {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
            } else if hasError {
                fallback()
            } else {
                ProgressView()
            }
        }
        .task {
            if let data = await ImageCache.shared.loadImageData(for: url),
               let loadedImage = NSImage(data: data) {
                
                if let bgRemoved = loadedImage.removingBackground(tolerance: 0.15) {
                    if let croppedImage = bgRemoved.croppedLeavingMargin() {
                        let tintedImage = croppedImage.tinted(with: NSColor.white)
                        self.image = tintedImage
                    } else {
                        self.image = bgRemoved.tinted(with: NSColor.white)
                    }
                } else {
                    self.image = loadedImage.tinted(with: NSColor.white)
                }

            } else {
                self.hasError = true
            }
        }

    }
}



extension NSImage {
    
    func tinted(with color: NSColor) -> NSImage {
        let newImage = NSImage(size: self.size, flipped: false) { (dstRect) -> Bool in
            self.draw(in: dstRect)
            NSGraphicsContext.current?.cgContext.setBlendMode(.sourceIn)
            color.setFill()
            dstRect.fill()
            return true
        }
        return newImage
    }
    
    func removingBackground(tolerance: CGFloat = 0.1) -> NSImage? {
        guard let tiffData = self.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiffData) else {
            return nil
        }

        let width = bitmap.pixelsWide
        let height = bitmap.pixelsHigh

        // Comprueba si ya tiene transparencia (alfa < 255 en algún pixel)
        for y in 0..<height {
            for x in 0..<width {
                let alpha = bitmap.colorAt(x: x, y: y)?.alphaComponent ?? 1.0
                if alpha < 1.0 {
                    // Ya tiene transparencia, no hacer nada
                    return self
                }
            }
        }

        // Función para obtener el color promedio de las esquinas
        func averageCornerColor() -> NSColor? {
            guard let c1 = bitmap.colorAt(x: 0, y: 0),
                  let c2 = bitmap.colorAt(x: width - 1, y: 0),
                  let c3 = bitmap.colorAt(x: 0, y: height - 1),
                  let c4 = bitmap.colorAt(x: width - 1, y: height - 1) else {
                return nil
            }
            let r = (c1.redComponent + c2.redComponent + c3.redComponent + c4.redComponent) / 4.0
            let g = (c1.greenComponent + c2.greenComponent + c3.greenComponent + c4.greenComponent) / 4.0
            let b = (c1.blueComponent + c2.blueComponent + c3.blueComponent + c4.blueComponent) / 4.0
            return NSColor(calibratedRed: r, green: g, blue: b, alpha: 1.0)
        }

        guard let bgColor = averageCornerColor() else {
            return nil
        }

        // Crea contexto para modificar la imagen
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return nil
        }

        guard let cgImage = self.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            return nil
        }

        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))

        guard let data = context.data else { return nil }
        let pixelBuffer = data.bindMemory(to: UInt8.self, capacity: width * height * 4)

        // Umbral de tolerancia (0 a 1) para definir “cercano” al color de fondo
        func colorCloseToBackground(r: UInt8, g: UInt8, b: UInt8) -> Bool {
            // Convierte bgColor a valores 0-255
            let br = UInt8(bgColor.redComponent * 255)
            let bg = UInt8(bgColor.greenComponent * 255)
            let bb = UInt8(bgColor.blueComponent * 255)

            // Calcula distancia Euclidiana simple normalizada
            let dr = Int(r) - Int(br)
            let dg = Int(g) - Int(bg)
            let db = Int(b) - Int(bb)
            let distance = sqrt(Double(dr*dr + dg*dg + db*db)) / sqrt(3 * 255 * 255) // Normaliza a [0,1]

            return distance < Double(tolerance)
        }

        for y in 0..<height {
            for x in 0..<width {
                let i = (y * width + x) * 4
                let r = pixelBuffer[i]
                let g = pixelBuffer[i + 1]
                let b = pixelBuffer[i + 2]
                let a = pixelBuffer[i + 3]

                if a == 0 { continue } // Ya transparente

                if colorCloseToBackground(r: r, g: g, b: b) {
                    // Hacer pixel transparente
                    pixelBuffer[i + 3] = 0
                }
            }
        }

        guard let outputCGImage = context.makeImage() else { return nil }
        return NSImage(cgImage: outputCGImage, size: self.size)
    }
    
    func croppedLeavingMargin(marginPercent: CGFloat = 0.05) -> NSImage? {
            guard let cgImage = self.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
            let width = cgImage.width
            let height = cgImage.height

            guard let dataProvider = cgImage.dataProvider,
                  let data = dataProvider.data else { return nil }

            let ptr = CFDataGetBytePtr(data)
            let bytesPerPixel = 4
            let bytesPerRow = cgImage.bytesPerRow

            // Find left bound: first column with any pixel alpha > 0
            var leftBound = 0
            outerLeft: for x in 0..<width {
                for y in 0..<height {
                    let idx = y * bytesPerRow + x * bytesPerPixel
                    let alpha = ptr![idx + 3]
                    if alpha > 0 {
                        leftBound = x
                        break outerLeft
                    }
                }
            }

            // Find right bound: last column with any pixel alpha > 0
            var rightBound = width - 1
            outerRight: for x in (0..<width).reversed() {
                for y in 0..<height {
                    let idx = y * bytesPerRow + x * bytesPerPixel
                    let alpha = ptr![idx + 3]
                    if alpha > 0 {
                        rightBound = x
                        break outerRight
                    }
                }
            }

            // Find top bound: first row with any pixel alpha > 0
            var topBound = 0
            outerTop: for y in 0..<height {
                for x in 0..<width {
                    let idx = y * bytesPerRow + x * bytesPerPixel
                    let alpha = ptr![idx + 3]
                    if alpha > 0 {
                        topBound = y
                        break outerTop
                    }
                }
            }

            // Find bottom bound: last row with any pixel alpha > 0
            var bottomBound = height - 1
            outerBottom: for y in (0..<height).reversed() {
                for x in 0..<width {
                    let idx = y * bytesPerRow + x * bytesPerPixel
                    let alpha = ptr![idx + 3]
                    if alpha > 0 {
                        bottomBound = y
                        break outerBottom
                    }
                }
            }

            let marginX = Int(CGFloat(width) * marginPercent)
            let marginY = Int(CGFloat(height) * marginPercent)

            let cropX = max(leftBound - marginX, 0)
            let cropY = max(topBound - marginY, 0)
            let cropWidth = min(rightBound + marginX, width - 1) - cropX + 1
            let cropHeight = min(bottomBound + marginY, height - 1) - cropY + 1

            let cropRect = CGRect(x: cropX, y: cropY, width: cropWidth, height: cropHeight)

            guard let croppedCGImage = cgImage.cropping(to: cropRect) else { return nil }

            let croppedRep = NSBitmapImageRep(cgImage: croppedCGImage)
            let croppedImage = NSImage(size: NSSize(width: cropWidth, height: cropHeight))
            croppedImage.addRepresentation(croppedRep)
            croppedImage.size = NSSize(width: cropWidth, height: cropHeight)

            return croppedImage
        }
}
