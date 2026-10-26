# Media upload

ChineseModels must be able to fetch the prepared video and every reference
image. The workflow registers each file with ChineseModels' own reference-media
store and passes the returned URL to the model — there is no third-party host and
no storage account to configure.

## Reference media — POST /api/reference-media

`media_host.upload(path)` sends multipart `file`, `kind` (`video` for
`.mp4/.mov/.webm`, otherwise `image`) and `model`, authenticated with your
`sk-cm-…` key, and returns the `url` from the response.

What gets uploaded per job:

- the **colored-depth composite** with the +3-semitone isolated vocals embedded
  (the source video the model edits), and
- each **character reference** image or video.

Uploads run in parallel (up to three at a time). A failed upload raises before
any generation is quoted or submitted, so it can never spend credits.

## Why there is no external host any more

The original workflow uploaded to Tmpfiles/Catbox because the previous provider
needed public URLs and had no storage of its own. ChineseModels provides the
reference-media store, so the Tmpfiles/Catbox adapters and their
`MEDIA_HOST`, `MEDIA_HOST_FALLBACKS` and `CATBOX_USERHASH` settings were removed.

## Expiry

The provider stores reference media itself, so there are no expiring third-party
links to refresh. Quote ids do expire, though — a stale quote is rejected and
must be re-requested rather than reused.
