import argparse
from datetime import datetime
import os
import logging
from logging import getLogger
import tempfile
import threading
import time
import operator
import requests
import coloredlogs
from dotenv import load_dotenv
import serial

logger = getLogger("runner")
coloredlogs.install(level="INFO")
api = None
installer = None
rebooter = None

class API:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key

    def request(self, method, path, **kwargs):
        kwargs.setdefault("headers", {})
        kwargs["headers"]["Authorization"] = f"bearer {self.api_key}"
        resp = requests.request(method, self.url + path, **kwargs)
        resp.raise_for_status()
        return resp

    def get(self, path, **kwargs):
        return self.request("get", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("post", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("put", path, **kwargs)

class GpioRebooter:
    def __init__(self):
        pass

    def reboot(self):
        pass

class CpInstaller:
    def __init__(self, install_path):
        self.dest = install_path

    def install(self):
        with tempfile.NamedTemporaryFile as tmp:
            open(tmp.name, "wb").write(image)
            os.rename(tmp.name, self.dest)

last_build_id = datetime.utcnow().timestamp()
def get_next_build(polling_interval):
    global last_build_id
    logger.info("watching for new builds...")
    while True:
        new_builds = api.get("/api/builds", params={ "newer_than": last_build_id }).json()
        if len(new_builds) > 0:
            last_build_id = new_builds[0]
            return new_builds[0]
        time.sleep(polling_interval)

def update_run_status(run_id, new_status):
    api.put(f"/api/runs/{run_id}", json={ "status": new_status })

def run_build(build):
    logger.info(f"Found a new build {build['id']}")
    image = api.get(f"/api/builds/{build['id']}/image").content

    run_id = api.post(f"/api/runs").json()["id"]
    installer.install(image)

    # start_reading_serial()
    rebooter.reboot()

    update_run_status(run_id, "booting")

def hearbeating(runner_name, machine):
    while True:
        api.put(f"/api/runners/{runner_name}", json={
            "name": runner_name,
            "machine": machine,
        })
        time.sleep(5 * 60)

def main():
    global api, installer, rebooter
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="The runner name.")
    parser.add_argument("--machine", required=True, help="The machine type.")
    parser.add_argument("--url", required=True, help="The BareMetal CI Server URL.")
    parser.add_argument("--api-key", help="The API Key.")
    parser.add_argument("--polling-interval", type=int, default=3)
    parser.add_argument("--install-by", choices=["cp"], required=True)
    parser.add_argument("--install-path",
        help="The destination path for the cp installer.")
    parser.add_argument("--reboot-by", choices=["gpio"], required=True)
    parser.add_argument("--serial-path", required=True)
    args = parser.parse_args()

    api_key = os.environ.get("BAREMETALCI_API_KEY", args.api_key)
    api = API(args.url, api_key)

    if args.install_by == "cp":
        if args.install_path:
            raise "--install-path is not set"
        installer = CpInstaller(args.install_path)

    if args.reboot_by == "gpio":
        rebooter = GpioRebooter()

    logger.info("starting")
    threading.Thread(target=hearbeating, args=(args.name, args.machine), daemon=True).start()
    while True:
        build = get_next_build(args.polling_interval)
        run_build(build)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl-C")
