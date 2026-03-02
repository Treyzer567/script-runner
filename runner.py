from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess, threading, time, os, logging, uuid

SCRIPTS_DIR = "/scripts"
LOG_DIR = "/logs"

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_DIR}/runner.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__)
CORS(app)  # <-- fixes your CORS issue

jobs = {}

def run_script(job_id, script_path):
    start = time.time()
    log_file = f"{LOG_DIR}/{job_id}.log"

    logging.info(f"START {script_path} job={job_id}")

    try:
        with open(log_file, "w") as f:
            proc = subprocess.run(
                ["python3", script_path],
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
                env=os.environ.copy() # Passes Sonarr API keys to the script
            )

        # Log the exit code for transparency
        logging.info(f"Job {job_id} exited with code {proc.returncode}")
        
        # If the script finishes with code 0, it's a success.
        # If it was killed by a timeout signal (-15 or -9), it will now show as failed
        # with a clear indicator in the logs.
        status = "success" if proc.returncode == 0 else "failed"
        
    except Exception as e:
        status = "failed"
        logging.error(f"Runner Exception for {job_id}: {e}")
        with open(log_file, "a") as f:
            f.write(f"\nRunner Error: {str(e)}")

    jobs[job_id]["status"] = status
    jobs[job_id]["end"] = time.time()
    logging.info(f"END {script_path} job={job_id} status={status}")

@app.route("/run/<script>", methods=["POST"])
def run(script):
    script_path = os.path.join(SCRIPTS_DIR, f"{script}.py")
    if not os.path.exists(script_path):
        return jsonify(error="Script not found"), 404

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "script": script,
        "status": "running",
        "start": time.time()
    }

    threading.Thread(
        target=run_script,
        args=(job_id, script_path),
        daemon=True
    ).start()

    return jsonify(job_id=job_id), 202

@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="Job not found"), 404
    return jsonify(job)

@app.route("/logs/<job_id>")
def logs(job_id):
    log_file = f"{LOG_DIR}/{job_id}.log"
    if not os.path.exists(log_file):
        return jsonify(error="Log not found"), 404
    return open(log_file).read(), 200, {"Content-Type": "text/plain"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8141)

