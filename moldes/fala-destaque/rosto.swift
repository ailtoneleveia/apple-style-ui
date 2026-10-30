// rosto.swift: os rostos de um vídeo, pelo Vision do macOS (local, sem download e sem rede).
//   swift rosto.swift <video.mp4> [passo em s, 0.2]
// Imprime um JSON por amostra: {"t": s, "rostos": [{"caixa": [x0,y0,x1,y1], "olhos": y, "boca": y, "queixo": y}]},
// em px do vídeo com y de cima para baixo. "olhos" é o topo dos olhos e das sobrancelhas, "boca" o pé dos lábios e
// "queixo" o pé do contorno do rosto (o Vision não acha o pé da barba: o montar.py dá margem).
import AVFoundation
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 2 else { FileHandle.standardError.write("uso: swift rosto.swift <video> [passo]\n".data(using: .utf8)!); exit(1) }
let passo = args.count >= 3 ? Double(args[2]) ?? 0.2 : 0.2
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero
let dur = CMTimeGetSeconds(asset.duration)
var t = 0.0
var linhas: [String] = []
while t < dur - 0.01 {
  if let img = try? gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
    let W = Double(img.width), H = Double(img.height)
    let req = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
    var rs: [String] = []
    for f in req.results ?? [] {
      let b = f.boundingBox  // normalizado, origem embaixo à esquerda
      let x0 = b.minX * W, x1 = b.maxX * W, y0 = (1 - b.maxY) * H, y1 = (1 - b.minY) * H
      let ys = { (r: VNFaceLandmarkRegion2D?) -> [Double] in
        (r?.pointsInImage(imageSize: CGSize(width: W, height: H)) ?? []).map { H - Double($0.y) } }
      let olhos = (ys(f.landmarks?.leftEye) + ys(f.landmarks?.rightEye) + ys(f.landmarks?.leftEyebrow) + ys(f.landmarks?.rightEyebrow)).min() ?? (y0 + 0.25 * (y1 - y0))
      let boca = (ys(f.landmarks?.outerLips)).max() ?? (y0 + 0.85 * (y1 - y0))
      let queixo = max((ys(f.landmarks?.faceContour)).max() ?? y1, y1)
      rs.append(String(format: "{\"caixa\": [%.0f, %.0f, %.0f, %.0f], \"olhos\": %.0f, \"boca\": %.0f, \"queixo\": %.0f}", x0, y0, x1, y1, olhos, boca, queixo))
    }
    linhas.append(String(format: "{\"t\": %.3f, \"rostos\": [", t) + rs.joined(separator: ", ") + "]}")
  }
  t += passo
}
print("[\n" + linhas.joined(separator: ",\n") + "\n]")
