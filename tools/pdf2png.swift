import PDFKit
import AppKit
let args = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: args[1]))!
let outDir = args[2]
let pages = args[3].split(separator: ",").map { Int($0)! }
let scale: CGFloat = args.count > 4 ? CGFloat(Double(args[4])!) : 1.6
for p in pages {
    guard let page = doc.page(at: p - 1) else { continue }
    let box = page.bounds(for: .mediaBox)
    let size = NSSize(width: box.width * scale, height: box.height * scale)
    let img = NSImage(size: size)
    img.lockFocus()
    NSColor.white.set(); NSRect(origin: .zero, size: size).fill()
    let ctx = NSGraphicsContext.current!.cgContext
    ctx.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: ctx)
    img.unlockFocus()
    let rep = NSBitmapImageRep(data: img.tiffRepresentation!)!
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(outDir)/p\(p).png"))
}
