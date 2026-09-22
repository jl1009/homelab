#!/usr/bin/env python3
import os
import sys
import time
import json
import urllib.request
import urllib.error
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    document_id = os.environ.get("DOCUMENT_ID")
    file_name = os.environ.get("DOCUMENT_FILE_NAME", "")
    archive_path = os.environ.get("DOCUMENT_ARCHIVE_PATH")
    source_path = os.environ.get("DOCUMENT_SOURCE_PATH")
    
    endpoint = os.environ.get("PAPERLESS_REMOTE_OCR_ENDPOINT")
    api_key = os.environ.get("PAPERLESS_REMOTE_OCR_API_KEY")
    api_token = os.environ.get("PAPERLESS_API_TOKEN")

    if not document_id:
        logging.error("DOCUMENT_ID not found in environment.")
        sys.exit(1)
        
    if not endpoint or not api_key:
        logging.error("Azure credentials not configured.")
        sys.exit(1)

    # We prefer the archive path (with text layer) if it exists, otherwise source
    pdf_path = archive_path if archive_path and os.path.exists(archive_path) else source_path
    if not pdf_path or not os.path.exists(pdf_path):
        logging.error(f"Cannot find PDF file. Archive: {archive_path}, Source: {source_path}")
        sys.exit(1)

    if not pdf_path.lower().endswith(".pdf"):
        logging.info("Document is not a PDF. Skipping Markdown OCR.")
        sys.exit(0)

    logging.info(f"Starting Azure Markdown OCR for Document ID {document_id}")

    endpoint = endpoint.rstrip('/')
    analyze_url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version=2024-02-29-preview&outputContentFormat=markdown"

    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
    except Exception as e:
        logging.error(f"Failed to read PDF: {e}")
        sys.exit(1)

    # 1. Submit to Azure
    req = urllib.request.Request(analyze_url, data=pdf_data, method='POST')
    req.add_header('Ocp-Apim-Subscription-Key', api_key)
    req.add_header('Content-Type', 'application/pdf')

    try:
        resp = urllib.request.urlopen(req)
        operation_location = resp.getheader('Operation-Location')
    except urllib.error.HTTPError as e:
        logging.error(f"Azure Analyze request failed: {e.code} {e.reason}")
        sys.exit(1)

    if not operation_location:
        logging.error("No Operation-Location header returned from Azure.")
        sys.exit(1)

    logging.info(f"Document submitted to Azure. Polling {operation_location}")

    # 2. Poll for completion
    poll_req = urllib.request.Request(operation_location, method='GET')
    poll_req.add_header('Ocp-Apim-Subscription-Key', api_key)

    max_retries = 60 # Up to 30 mins for massive PDFs
    wait_time = 5
    result_json = None

    for attempt in range(max_retries):
        try:
            poll_resp = urllib.request.urlopen(poll_req)
            result_json = json.loads(poll_resp.read().decode('utf-8'))
            status = result_json.get("status")
            
            if status == "succeeded":
                break
            elif status == "failed":
                logging.error(f"Azure processing failed: {result_json}")
                sys.exit(1)
            
            logging.info(f"Status is {status}. Waiting {wait_time}s...")
        except urllib.error.HTTPError as e:
            logging.error(f"Azure Polling request failed: {e.code} {e.reason}")
            sys.exit(1)

        time.sleep(wait_time)
        wait_time = min(wait_time + 5, 30) # exponential-ish backoff up to 30s
    else:
        logging.error("Timeout waiting for Azure to complete processing.")
        sys.exit(1)

    # 3. Extract Markdown
    markdown_content = result_json.get("analyzeResult", {}).get("content")
    if not markdown_content:
        logging.error("No content found in Azure response.")
        sys.exit(1)

    logging.info(f"Markdown successfully retrieved. Length: {len(markdown_content)}")

    # 4. Update Paperless
    paperless_url = f"http://localhost:8000/api/documents/{document_id}/"
    update_data = json.dumps({"content": markdown_content}).encode('utf-8')
    update_req = urllib.request.Request(paperless_url, data=update_data, method='PATCH')
    update_req.add_header('Authorization', f'Token {api_token}')
    update_req.add_header('Content-Type', 'application/json')
    update_req.add_header('Accept', 'application/json')

    try:
        urllib.request.urlopen(update_req)
        logging.info(f"Successfully updated content for Document {document_id} with Azure Markdown.")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logging.error(f"Failed to update Paperless content: {e.code} {error_body}")
        sys.exit(1)

if __name__ == "__main__":
    main()
