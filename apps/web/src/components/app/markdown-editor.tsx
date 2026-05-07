"use client";

import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { Markdown } from "tiptap-markdown";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

/** WYSIWYG editor that exposes its content as markdown.
 *
 *  Why we needed this: paste from Google Docs / a CMS used to land in a
 *  plain ``<textarea>`` and lose its formatting. With tiptap the paste
 *  pipeline parses the clipboard HTML into a structured doc; we then ask
 *  ``tiptap-markdown`` to serialise that doc back to markdown so the
 *  rest of the pipeline (detection / retrieval / report rendering) keeps
 *  working on a single string source.
 *
 *  The component is fully controlled - the parent owns the markdown
 *  string in ``value`` / ``onChange``. We round-trip through tiptap on
 *  every keystroke so ``value`` is always the live serialised markdown.
 */
type Props = {
  value: string;
  onChange: (markdown: string) => void;
  disabled?: boolean;
  className?: string;
  minHeightClassName?: string;
};

export function MarkdownEditor({
  value,
  onChange,
  disabled,
  className,
  minHeightClassName = "min-h-[240px]",
}: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Default link extension is shipped via StarterKit; we override
        // with our own to disable click-to-navigate inside the editor
        // (otherwise marking text inside an HTML-pasted link opens it).
        link: false,
      }),
      Link.configure({
        openOnClick: false,
        autolink: true,
        protocols: ["http", "https", "mailto"],
        HTMLAttributes: {
          class: "text-primary underline",
        },
      }),
      Markdown.configure({
        html: false,
        transformPastedText: true,
        transformCopiedText: false,
        breaks: true,
        linkify: true,
      }),
    ],
    content: value || "",
    editable: !disabled,
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      const storage = editor.storage as {
        markdown?: { getMarkdown: () => string };
      };
      const md = storage.markdown?.getMarkdown() ?? editor.getText();
      onChange(md);
    },
  });

  // Push external value changes (e.g. PDF/URL extraction filling the
  // editor, or "Erneut prüfen" replacing the source with the rewritten
  // version) into the tiptap document. Skip when the editor already has
  // the same content - otherwise every keystroke would round-trip.
  useEffect(() => {
    if (!editor) return;
    const storage = editor.storage as {
      markdown?: { getMarkdown: () => string };
    };
    const current = storage.markdown?.getMarkdown() ?? editor.getText();
    if (current === value) return;
    editor.commands.setContent(value || "", { emitUpdate: false });
  }, [editor, value]);

  // Reflect the parent disabled flag onto the editor instance so the
  // textarea visibly locks during analysis.
  useEffect(() => {
    if (!editor) return;
    editor.setEditable(!disabled);
  }, [editor, disabled]);

  return (
    <div
      className={cn(
        "prose prose-sm max-w-none cursor-text overflow-y-auto px-5 py-5 font-serif text-[15px] leading-[1.85] text-foreground",
        "prose-headings:font-serif prose-headings:tracking-tight prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary prose-li:my-1",
        "[&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-full",
        minHeightClassName,
        disabled && "opacity-70",
        className,
      )}
      onClick={() => editor?.chain().focus().run()}
    >
      <EditorContent editor={editor} />
    </div>
  );
}
