class MediaProcessor:
    def extract_media_from_post(self, post_data):
        """Extract all media (images, videos, links) from a post"""
        media = {"images": [], "videos": [], "links": [], "other_attachments": []}

        # Direct image from post
        if "full_picture" in post_data:
            media["images"].append(
                {
                    "url": post_data["full_picture"],
                    "type": "post_image",
                    "title": "Full Picture",
                }
            )

        # Thumbnail image (if different from full picture)
        if "picture" in post_data and post_data.get("picture") != post_data.get(
            "full_picture"
        ):
            media["images"].append(
                {
                    "url": post_data["picture"],
                    "type": "post_thumbnail",
                    "title": "Thumbnail",
                }
            )

        # Process attachments (if available)
        if "attachments" in post_data and "data" in post_data["attachments"]:
            for attachment in post_data["attachments"]["data"]:
                attachment_type = attachment.get("type", "unknown")

                if attachment_type == "photo":
                    if "media" in attachment and "image" in attachment["media"]:
                        media["images"].append(
                            {
                                "url": attachment["media"]["image"].get("src", ""),
                                "type": "attachment_image",
                                "title": attachment.get("title", ""),
                            }
                        )

                elif attachment_type in ["video_inline", "video_autoplay"]:
                    if "media" in attachment:
                        if "source" in attachment["media"]:
                            media["videos"].append(
                                {
                                    "url": attachment["media"]["source"],
                                    "type": "attachment_video",
                                    "title": attachment.get("title", ""),
                                }
                            )
                        if "image" in attachment["media"]:
                            media["images"].append(
                                {
                                    "url": attachment["media"]["image"].get("src", ""),
                                    "type": "video_thumbnail",
                                    "title": attachment.get("title", "")
                                    + " (thumbnail)",
                                }
                            )

                elif attachment_type in ["share", "link"]:
                    media["links"].append(
                        {
                            "url": attachment.get("url", ""),
                            "title": attachment.get("title", ""),
                            "description": attachment.get("description", ""),
                            "type": "shared_link",
                        }
                    )

                else:
                    media["other_attachments"].append(
                        {
                            "type": attachment_type,
                            "title": attachment.get("title", ""),
                            "url": attachment.get("url", ""),
                        }
                    )

        return media

    def merge_scraped_media(self, api_media, scraped_media):
        """Merge API and scraped media, avoiding duplicates"""
        # Merge scraped media (avoid duplicates)
        for img in scraped_media["images"]:
            if not any(
                existing["url"] == img["url"] for existing in api_media["images"]
            ):
                api_media["images"].append(img)

        for vid in scraped_media["videos"]:
            if not any(
                existing["url"] == vid["url"] for existing in api_media["videos"]
            ):
                api_media["videos"].append(vid)

        return api_media

    def count_media_items(self, media):
        """Count different types of media"""
        return {
            "images": len(media["images"]),
            "videos": len(media["videos"]),
            "links": len(media["links"]),
            "other_attachments": len(media["other_attachments"]),
            "total": len(media["images"])
            + len(media["videos"])
            + len(media["links"])
            + len(media["other_attachments"]),
        }
