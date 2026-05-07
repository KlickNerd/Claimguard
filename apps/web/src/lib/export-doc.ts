import {
  AlignmentType,
  Document,
  ExternalHyperlink,
  HeadingLevel,
  Packer,
  Paragraph,
  TextRun,
} from "docx";
import { marked, type Token, type Tokens } from "marked";

/** Export the rewritten claim text as a real ``.docx``.
 *
 *  We tried the HTML-in-``.doc`` trick first - Word and LibreOffice both
 *  open that, but Pages refuses with a "Datei kann nicht geöffnet werden"
 *  error. The dolanmiu ``docx`` library produces ECMA-376 OOXML that
 *  every modern word processor reads, so we convert markdown -> tokens
 *  via ``marked.lexer`` and map onto docx ``Paragraph`` / ``TextRun``.
 *
 *  We only handle the markdown features that the rest of ClaimGuard
 *  actually uses: H1-H3, paragraphs, ordered/unordered lists, inline
 *  bold / italic / inline code / links, blockquotes and horizontal
 *  rules. Everything else falls through to plain text - good enough
 *  for marketing copy. */
export async function downloadAsDoc(
  markdown: string,
  filename: string,
): Promise<void> {
  const safeFilename = filename.endsWith(".docx")
    ? filename
    : `${filename}.docx`;
  const document = buildDocument(markdown);
  const blob = await Packer.toBlob(document);
  const url = URL.createObjectURL(blob);
  const anchor = document_createAnchor(url, safeFilename);
  anchor.click();
  document_cleanup(anchor, url);
}

// Wrap the DOM ops so the heavy lifting in ``downloadAsDoc`` stays focused.
function document_createAnchor(url: string, filename: string): HTMLAnchorElement {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  return anchor;
}

function document_cleanup(anchor: HTMLAnchorElement, url: string): void {
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function buildDocument(markdown: string): Document {
  const tokens = marked.lexer(markdown || "");
  const children: Paragraph[] = [];
  for (const token of tokens) {
    children.push(...renderBlock(token));
  }
  if (children.length === 0) {
    children.push(new Paragraph({ children: [new TextRun("")] }));
  }
  return new Document({
    creator: "ClaimGuard",
    title: "ClaimGuard-Report",
    styles: {
      paragraphStyles: [
        {
          id: "Normal",
          name: "Normal",
          run: { font: "Calibri", size: 22 }, // 11 pt
          paragraph: { spacing: { after: 160 } },
        },
      ],
    },
    sections: [{ properties: {}, children }],
  });
}

function renderBlock(token: Token): Paragraph[] {
  switch (token.type) {
    case "heading":
      return [renderHeading(token as Tokens.Heading)];
    case "paragraph":
      return [
        new Paragraph({
          children: renderInline((token as Tokens.Paragraph).tokens ?? []),
        }),
      ];
    case "list":
      return renderList(token as Tokens.List);
    case "blockquote":
      return renderBlockquote(token as Tokens.Blockquote);
    case "code":
      return [
        new Paragraph({
          children: [
            new TextRun({
              text: (token as Tokens.Code).text,
              font: "Consolas",
            }),
          ],
        }),
      ];
    case "hr":
      return [
        new Paragraph({
          border: { bottom: { color: "CCCCCC", space: 1, style: "single", size: 6 } },
        }),
      ];
    case "space":
      return [];
    case "html":
      // Strip raw HTML to plain text - the report doesn't carry trusted
      // HTML, and Pages would otherwise show angle brackets.
      return [
        new Paragraph({
          children: [new TextRun(stripHtml((token as Tokens.HTML).text))],
        }),
      ];
    default: {
      const fallback = (token as { raw?: string; text?: string }).text
        ?? (token as { raw?: string }).raw
        ?? "";
      return fallback
        ? [new Paragraph({ children: [new TextRun(fallback)] })]
        : [];
    }
  }
}

function renderHeading(token: Tokens.Heading): Paragraph {
  const level =
    token.depth === 1
      ? HeadingLevel.HEADING_1
      : token.depth === 2
        ? HeadingLevel.HEADING_2
        : token.depth === 3
          ? HeadingLevel.HEADING_3
          : HeadingLevel.HEADING_4;
  return new Paragraph({
    heading: level,
    alignment: AlignmentType.LEFT,
    children: renderInline(token.tokens ?? [{ type: "text", raw: token.text, text: token.text } as Tokens.Text]),
  });
}

function renderList(list: Tokens.List): Paragraph[] {
  const out: Paragraph[] = [];
  list.items.forEach((item, idx) => {
    out.push(...renderListItem(item, list.ordered ?? false, idx));
  });
  return out;
}

function renderListItem(
  item: Tokens.ListItem,
  ordered: boolean,
  index: number,
): Paragraph[] {
  const inlineTokens =
    (item.tokens ?? []).flatMap((t) =>
      t.type === "text"
        ? ((t as Tokens.Text).tokens ?? [{ type: "text", raw: (t as Tokens.Text).text, text: (t as Tokens.Text).text } as Tokens.Text])
        : t.type === "paragraph"
          ? ((t as Tokens.Paragraph).tokens ?? [])
          : [t],
    );

  const paragraph = new Paragraph({
    children: renderInline(inlineTokens),
    bullet: ordered ? undefined : { level: 0 },
    numbering: ordered ? { reference: "claimguard-numbered", level: 0 } : undefined,
  });
  void index; // kept for future numbering offsets
  return [paragraph];
}

function renderBlockquote(token: Tokens.Blockquote): Paragraph[] {
  const inner = (token.tokens ?? []) as Token[];
  return inner.flatMap(renderBlock).map(
    (p) =>
      new Paragraph({
        // Render quote text as italic + grey instead of building a real
        // border; that's good enough for marketing copy and avoids a
        // numbering/border definition cascade.
        children: paragraphRunsAsItalicGrey(p),
        indent: { left: 480 },
      }),
  );
}

function paragraphRunsAsItalicGrey(p: Paragraph): TextRun[] {
  // ``Paragraph`` doesn't expose its children publicly; we work around by
  // re-rendering as a single italic+grey run from the source text. The
  // blockquote path is rare in our data, so the loss of nested format is
  // acceptable.
  const text = (p as unknown as { rootKey: string; root: { children?: Array<{ properties?: { text?: string } }> } }).root?.children
    ?.map((c) => c?.properties?.text ?? "")
    .join("") ?? "";
  return [new TextRun({ text, italics: true, color: "555555" })];
}

function renderInline(tokens: Token[]): TextRun[] {
  const runs: TextRun[] = [];
  for (const tok of tokens) {
    runs.push(...renderInlineToken(tok));
  }
  return runs;
}

function renderInlineToken(tok: Token, modifiers: { bold?: boolean; italics?: boolean } = {}): TextRun[] {
  switch (tok.type) {
    case "text":
      // ``Tokens.Text`` may itself contain nested inline tokens (e.g.
      // when a list item carries inline formatting).
      if ((tok as Tokens.Text).tokens) {
        return ((tok as Tokens.Text).tokens ?? []).flatMap((t) =>
          renderInlineToken(t, modifiers),
        );
      }
      return [
        new TextRun({
          text: decodeEntities((tok as Tokens.Text).text ?? ""),
          ...modifiers,
        }),
      ];
    case "strong":
      return ((tok as Tokens.Strong).tokens ?? []).flatMap((t) =>
        renderInlineToken(t, { ...modifiers, bold: true }),
      );
    case "em":
      return ((tok as Tokens.Em).tokens ?? []).flatMap((t) =>
        renderInlineToken(t, { ...modifiers, italics: true }),
      );
    case "codespan":
      return [
        new TextRun({
          text: (tok as Tokens.Codespan).text,
          font: "Consolas",
          ...modifiers,
        }),
      ];
    case "link": {
      const link = tok as Tokens.Link;
      const inner = (link.tokens ?? []).flatMap((t) =>
        renderInlineToken(t, { ...modifiers }),
      );
      return [
        new ExternalHyperlink({
          link: link.href,
          children: inner.length > 0 ? inner : [new TextRun({ text: link.text, ...modifiers })],
        }) as unknown as TextRun, // ExternalHyperlink is accepted in Paragraph children even though the type signature is narrower.
      ];
    }
    case "br":
      return [new TextRun({ text: "", break: 1, ...modifiers })];
    case "del":
      return ((tok as Tokens.Del).tokens ?? []).flatMap((t) =>
        renderInlineToken(t, { ...modifiers }),
      ).map((r) => r);
    case "html":
      return [new TextRun({ text: stripHtml((tok as Tokens.HTML).text), ...modifiers })];
    default: {
      const text = (tok as { text?: string; raw?: string }).text
        ?? (tok as { raw?: string }).raw
        ?? "";
      return text ? [new TextRun({ text, ...modifiers })] : [];
    }
  }
}

function decodeEntities(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

function stripHtml(s: string): string {
  return s.replace(/<[^>]+>/g, "");
}
