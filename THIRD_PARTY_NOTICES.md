# Third-party design resources

The offline report includes a small, vendored subset of Open Props and Lucide. It makes no network requests for styling, icons or fonts. Their licenses remain separate from the extension's GPL-3.0-only license.

## Open Props

Source: https://github.com/argyleink/open-props

Pinned revision: `f39ab7c377a0e047f930982e3611bbc95254a260`

The report uses the gray tokens from `src/props.gray.css` and the `--size-1` through `--size-7` spacing tokens from `src/props.sizes.css`. The values are unchanged. The selected declarations are combined in `evidence_wiki/design/open-props.css`.

Copyright (c) 2021 Adam Argyle. MIT license. The full license is in `evidence_wiki/design/LICENSE.open-props`.

## Lucide

Source: https://github.com/lucide-icons/lucide

Pinned revision: `4b203ec9b6002fd74fd5dadc8612220e64289305`

The report uses the unchanged `files.svg` and `search.svg` files from the upstream `icons` directory. The files icon identifies the document workspace. The search icon identifies the claim search field. CSS adjusts their display dimensions and color. Their containers hide them from assistive technology because visible text already labels these controls.

Copyright (c) 2026 Lucide Icons and Contributors. ISC license. The search icon derives from Feather, Copyright (c) 2013-present Cole Bemis, under the MIT license. The full upstream license, including the Feather notice, is in `evidence_wiki/design/LICENSE.lucide`.

## Distribution

The wheel includes the tokens, icons, report styles and both full license files. Each exported HTML file embeds the resources and the full license texts. The notices remain in the inert `third-party-notices` template in the HTML source. No external resources are required to retain or read them.
