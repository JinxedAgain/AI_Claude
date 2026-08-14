# Refuge — adding your own art & chant

## Holy images (backgrounds)

Drop JPGs into `site/faith/art/` named `1.jpg`, `2.jpg`, … up to `16.jpg`.
The app checks for them on every launch and prefers them over everything else.

Until then, the app tries a set of famous public-domain sacred paintings
hotlinked from Wikimedia Commons (Rembrandt, Murillo, the Sinai Pantocrator…).
Any image that fails to load falls back to the built-in stained-glass windows,
so a broken link never shows.

Good sources for public-domain sacred art: Wikimedia Commons, the National
Gallery open collection, the Rijksmuseum, the Met's open-access collection.
Portrait-orientation crops look best (the screen is tall).

## Gregorian chant (background audio)

Drop MP3s into `site/faith/audio/` named `chant1.mp3` … `chant4.mp3`.
The app probes for them when the feed opens; if any exist they play in a
loop (and the toggle in the top-right of the feed turns them on/off).

Until real chant files exist, a soft generated sacred drone plays instead.

Free, legal chant recordings: Wikimedia Commons (category "Gregorian chant"),
Internet Archive (search "Gregorian chant" with public-domain filter), and
Musopen. Keep files modest (~2–8 MB each) so they load fast on cellular.

## After adding files

Commit and push to the deployed branch (or ask Claude to). Also copy the new
files into `ios/Refuge/Web/` if you use the native iOS app, so they ship in
the app bundle.
