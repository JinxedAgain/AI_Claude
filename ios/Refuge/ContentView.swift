import SwiftUI
import WebKit

/// Hosts the Refuge web app (bundled in Web/index.html) full-screen,
/// with a JS→native bridge for real Taptic-engine haptics.
struct ContentView: UIViewRepresentable {
    final class Coordinator: NSObject, WKScriptMessageHandler {
        private let tap = UIImpactFeedbackGenerator(style: .light)

        func userContentController(_ userContentController: WKUserContentController,
                                   didReceive message: WKScriptMessage) {
            if message.name == "haptic" {
                tap.prepare()
                tap.impactOccurred(intensity: 0.7)
            }
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.userContentController.add(context.coordinator, name: "haptic")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.039, green: 0.059, blue: 0.118, alpha: 1)
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.bounces = false
        webView.allowsBackForwardNavigationGestures = false

        if let url = Bundle.main.url(forResource: "index", withExtension: "html") {
            webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        }
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
