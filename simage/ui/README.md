# Simage UI

A fast, multi-tab image pipeline UI for the Simage project.

- High-speed thumbnail gallery for 1000s of images
- Tabs for gallery/search, tags, edit, batch, settings, full image viewer, and DB viewer

## Getting Started

Launch the UI:

```powershell
python -m simage.ui.app
```

## What Each Tab Does

- Gallery & Search: thumbnail grid, metadata preview, tag filter dropdown, sort options, and keyboard navigation.
- Tag Images: manage tags, rename tags, add tags to images, and maintain custom tags in `out/tag_list.json`.
- Batch Processing: import folders into `Input/`, batch tag/rename/move, export metadata JSON, and refresh the pipeline.
- Settings: create `.venv`, install dependencies, run EXIF/ingest/resources/resolve/all, and restart the UI.
- DB Viewer: connect/browse DB, list tables, run SQL with history, export CSV, and copy rows/cells.
- Edit Images / Full Image Viewer: placeholders for future tools.
