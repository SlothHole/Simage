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
- Gallery controls: thumbnail size/spacing sliders and persistent splitters.
- Tag Images: manage tags, rename tags, queue tag updates, and maintain custom tags in `out/tag_list.json`.
- Batch Processing: import folders into `Input/`, batch tag/rename/move, export metadata JSON, and refresh the pipeline.
- Edit Images: workflow search/anchor tools, editable prompt/model params, image details, and metadata strip actions.
- Settings: display themes/custom colors/font (saved in `out/ui_settings.json`), environment setup, pipeline actions, and restart the UI.
- DB Viewer: connect/browse DB, list tables, run SQL with history, export CSV, and copy rows/cells.
- Full Image Viewer: placeholder for future tools.
