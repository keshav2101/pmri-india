import os
import uvicorn
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("pmri.launcher")
    
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        logger.error(f"Invalid PORT environment variable: {port_str}. Defaulting to 8000.")
        port = 8000
        
    logger.info(f"Starting PMRI backend on 0.0.0.0:{port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
