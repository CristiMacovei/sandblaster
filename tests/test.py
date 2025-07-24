#!/usr/bin/env python3

from datetime import datetime
import pathlib
import os
import subprocess

DIRNAME = os.path.dirname(os.path.abspath(__file__))
MAINDIR = os.path.dirname(DIRNAME)

def compare_directories(actual:pathlib.Path, expected: pathlib.Path):
    actual_files = sorted(f.relative_to(actual) for f in actual.rglob("*") if f.is_file())
    expected_files = sorted(f.relative_to(expected) for f in expected.rglob("*") if f.is_file())

    assert actual_files == expected_files, "Mismatch in file names/structure"

    for rel_path in actual_files:
        actual_content = (actual / rel_path).read_bytes()
        expected_content = (expected / rel_path).read_bytes()
        assert actual_content == expected_content, f"Mismatch in file: {rel_path}"


def build_image():
	name = f'sandblaster-{datetime.now().strftime("%d_%m_%Y__%H_%M")}'

	subprocess.run([
		"docker", "build", "-t", name, MAINDIR
	])

	return name

def start_run(container_name):
	run_name = f"run_{container_name}"

	subprocess.run([
		"docker", "run",
		"-v", os.path.join(DIRNAME, "iPhone5__1_9.3_13E237") + ":" + "/test",
		"--rm", "-dit", "--name", run_name, container_name
	])

	return run_name

def stop_run(container_name, run_name):
	subprocess.run([
		"docker", "stop", run_name
	])
    

def test_iphone5_13E237(run_name, update_refs = False):
	print(f'Running extract_sandbox_data on firmware 9.3...')

	subprocess.run([
		"docker", "exec", run_name,
		"rm", "-rf", "/test/outputs"
	])

	subprocess.run([
		"docker", "exec", run_name,
		"mkdir", "/test/outputs"
	])

	subprocess.run([  #"echo",
		"docker", "exec", run_name,
		"/sandblaster/helpers/extract_sandbox_data.py", "-o", "/test/outputs/sb_ops", "/test/inputs/sandbox.kext", "9.3"
	])

	subprocess.run([  #"echo",
		"docker", "exec", run_name,
		"/sandblaster/helpers/extract_sandbox_data.py", "-O", "/test/outputs", "/test/inputs/sandbox.kext", "9.3"
	])

	subprocess.run([  #"echo",
		"docker", "exec", run_name,
		"mkdir", "/test/outputs/rev_profiles"
	])

	subprocess.run([#  "echo",
		"docker", "exec", run_name,
		"sh", "-c", "cd /sandblaster/reverse-sandbox/ && python2.7 reverse_sandbox.py -r 9.3 -o /test/outputs/sb_ops -d /test/outputs/rev_profiles/ /test/outputs/sandbox_bundle -psb > /test/outputs/sandbox_profiles.txt"
	])

	subprocess.run([  #"echo",
		"docker", "exec", run_name,
		"sh", "-c", "cd /sandblaster/reverse-sandbox/ && python2.7 reverse_sandbox.py -r 9.3 -o /test/outputs/sb_ops -d /test/outputs/rev_profiles/ /test/outputs/sandbox_bundle"
	])

	if update_refs:
		subprocess.run([
			"docker", "exec", run_name,
			"rm", "-rf", "/test/references"
		])

		subprocess.run([
			"docker", "exec", run_name,
			"cp", "-r", "/test/outputs", "/test/references"
		])

		return

	print(f'Comparing results...')	

	output_dir = pathlib.Path(DIRNAME, "iPhone5__1_9.3_13E237", "outputs")
	reference_dir = pathlib.Path(DIRNAME, "iPhone5__1_9.3_13E237", "references")

	try:
		compare_directories(output_dir, reference_dir)
	
		print("[PASS] iPhone5_13E237 :)")
	except AssertionError as err:
		print(f"[FAIL] iPhone5_13E237 - {err}")


def main():
	container_name = build_image()

	run_name = start_run(container_name)

	test_iphone5_13E237(run_name)
    
	stop_run(container_name, run_name)
	

main()
