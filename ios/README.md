# Refuge — iOS app & TestFlight guide

This folder is a complete Xcode project that wraps the Refuge web app
(`Refuge/Web/index.html`, a copy of `site/faith/index.html`) in a native
iOS shell. It runs fully offline and is ready to upload to **TestFlight**
(Apple's beta-testing service — the "testing thing").

## What you need

1. **A Mac** with Xcode 16 or newer (free from the Mac App Store).
2. **An Apple Developer Program membership** — $99/year at
   [developer.apple.com/programs](https://developer.apple.com/programs/).
   TestFlight and the App Store both require it. (A free Apple ID can
   install the app on your own phone via cable, but not TestFlight.)

## Build and run on your own iPhone (5 minutes)

1. Clone this repo on the Mac and open `ios/Refuge.xcodeproj` in Xcode.
2. Click the **Refuge** project in the sidebar → **Signing & Capabilities** tab:
   - Check **Automatically manage signing**.
   - Pick your **Team** (your Apple ID / developer account).
   - If the bundle ID `com.hlyfmly.refuge` is taken, change it to anything
     unique, e.g. `com.yourname.refuge`.
3. Plug in your iPhone, select it in the device menu at the top, press **▶ Run**.
   (First time: on the phone, Settings → General → VPN & Device Management →
   trust your developer certificate.)

## Upload to TestFlight

1. In [App Store Connect](https://appstoreconnect.apple.com) → **My Apps** →
   **＋** → **New App**: platform iOS, name **Refuge** (or your pick),
   language, the bundle ID from step 2 above, any SKU (e.g. `refuge001`).
2. In Xcode, select **Any iOS Device (arm64)** as the destination, then
   **Product → Archive**.
3. When the Organizer window opens: **Distribute App → App Store Connect →
   Upload**, accept the defaults, and wait for the upload to finish.
4. In App Store Connect → your app → **TestFlight** tab: the build appears
   after ~10–30 minutes of processing. Answer the export-compliance question
   (this app uses no encryption beyond HTTPS → answer **None of the
   algorithms mentioned above** / standard exemption).
5. **Internal testing**: add yourself (and up to 100 members) under
   *Internal Testing* — instant, no review. **External testing**: create a
   group, add up to 10,000 testers by email or public link — requires a quick
   beta review (usually a day). Testers install the **TestFlight** app from
   the App Store and open your invite.

## Updating the app

The native shell just displays `Refuge/Web/index.html`. When the web app in
`site/faith/index.html` changes, copy it over:

```sh
cp site/faith/index.html ios/Refuge/Web/index.html
```

Then in Xcode bump **General → Build** (e.g. 1 → 2), re-Archive, re-upload.
TestFlight testers get the new build automatically.

## Notes

- The stained-glass backgrounds are drawn in code, so no image assets are
  needed. If you add sacred-art images to the web app later, put copies in
  `Refuge/Web/` alongside `index.html` — the whole folder ships in the app.
- App icon lives at `Refuge/Assets.xcassets/AppIcon.appiconset/icon-1024.png`
  (single 1024×1024, no transparency, as Apple requires).
