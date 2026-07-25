"""
SQL statement templates for the storage backend.
"""

SQL_TEMPLATE_UPSERT_DOCUMENT = """
    INSERT INTO public.documents (
        source_path,
        filename,
        lang,
        manufacturer,
        model,
        page_count,
        empty_page_count,
        source_url,
        accessed_on,
        checksum_sha256
    ) VALUES (
        %(source_path)s,
        %(filename)s,
        %(lang)s,
        %(manufacturer)s,
        %(model)s,
        %(page_count)s,
        %(empty_page_count)s,
        %(source_url)s,
        %(accessed_on)s,
        %(checksum_sha256)s
    )
    ON CONFLICT (source_path) DO UPDATE SET
        filename = EXCLUDED.filename,
        lang = EXCLUDED.lang,
        manufacturer = EXCLUDED.manufacturer,
        model = EXCLUDED.model,
        page_count = EXCLUDED.page_count,
        empty_page_count = EXCLUDED.empty_page_count,
        source_url = EXCLUDED.source_url,
        accessed_on = EXCLUDED.accessed_on,
        checksum_sha256 = EXCLUDED.checksum_sha256
    RETURNING id
    """

SQL_TEMPLATE_DELETE_CHUNKS_FOR_DOCUMENT = """
    DELETE FROM public.chunks
    WHERE document_id = %(document_id)s
    """

SQL_TEMPLATE_INSERT_CHUNK = """
    INSERT INTO public.chunks (
        document_id,
        chunk_index,
        content,
        page_start,
        page_end,
        lang,
        token_estimate,
        embedding,
        embedding_model
    ) VALUES (
        %(document_id)s,
        %(chunk_index)s,
        %(content)s,
        %(page_start)s,
        %(page_end)s,
        %(lang)s,
        %(token_estimate)s,
        %(embedding)s,
        %(embedding_model)s
    )
    """
