import { useEffect } from "react";
import { site } from "@/config/site";

const BASE_TITLE = "FibreHood";

export function useDocumentMeta({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  useEffect(() => {
    document.title = title.includes(BASE_TITLE) ? title : `${title} | ${BASE_TITLE}`;
    if (description) {
      let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (!meta) {
        meta = document.createElement("meta");
        meta.name = "description";
        document.head.appendChild(meta);
      }
      meta.content = description;
    }
  }, [title, description]);
}

export const defaultDescription = site.description;
