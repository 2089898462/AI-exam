import uvicorn
import os
import sys

if __name__ == '__main__':
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)

    print(f"Starting server on port 8002 from {backend_dir}...")
    uvicorn.run('main:app', host='0.0.0.0', port=8002, reload=False)
