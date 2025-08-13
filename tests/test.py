#!/usr/bin/env python3

import sys
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
		# skip sb files as they are checked separately
		if rel_path.suffix == ".sb":
			continue

		else:
			actual_content = (actual / rel_path).read_bytes()
			expected_content = (expected / rel_path).read_bytes()
			assert actual_content == expected_content, f"Mismatch in file: {rel_path}"

	
	parser_proc = subprocess.run([
		os.path.join(MAINDIR, "sb_parser", "parser"),
		(actual / "rev_profiles"),
		(expected / "rev_profiles")
	])

	assert parser_proc.returncode == 0, f"Mismatch in file: {rel_path}"


def build_image():
	name = f'sandblaster_{datetime.now().strftime("%d_%m_%Y__%H_%M_%S")}'

	docker_build_process = subprocess.run([
		"sh", "-c", f"docker build -t {name} {MAINDIR} > {os.path.join(DIRNAME, 'build_logs', name)}.log"
	])

	if docker_build_process.returncode != 0:
		print(f'[ERROR] Docker build failed, check build_logs/{name}.log for more details :(')
		return 1

	print(f'[INFO] Docker build {name} successful')
	return name


def remove_image(container_name):
	print(f"[INFO] Removing container {container_name}")
	
	subprocess.run([
		"docker", "rmi", container_name
	])


def start_run(container_name, test_name):
	run_name = f"run_{container_name}_{test_name}"

	test_path = os.path.join(DIRNAME, test_name)

	print("[INFO] Run ID: ", end='')
	sys.stdout.flush()

	subprocess.run([
		"docker", "run",
		"-v", f"{test_path}:/test",
		"--rm", "-dit", "--name", run_name, container_name
	])

	return run_name

def stop_run(run_name):
	subprocess.run([
		"docker", "stop", run_name
	])


def generic_test(container_name, test_name, ios_major_version, ios_version, update_refs=False):
	run_name = start_run(container_name, test_name)

	print(f'[INFO] Running sandblaster test on {test_name} (iOS v{ios_major_version})...')

	subprocess.run([
		"docker", "exec", run_name,
		"rm", "-rf", "/test/outputs"
	])

	subprocess.run([
		"docker", "exec", run_name,
		"mkdir", "/test/outputs"
	])

	subprocess.run([
		"docker", "exec", run_name,
		"/sandblaster/helpers/extract_sandbox_data.py", "-o", "/test/outputs/sb_ops", "/test/inputs/sandbox.kext", ios_version
	])

	if ios_major_version >= 9:
		subprocess.run([
			"docker", "exec", run_name,
			"/sandblaster/helpers/extract_sandbox_data.py", 
			"-O", "/test/outputs", 
			"/test/inputs/sandbox.kext", ios_version
		])
	else:
		subprocess.run([
			"docker", "exec", run_name,
			"mkdir", "-p", "/test/outputs/sb_profiles"
		])

		subprocess.run([
			"docker", "exec", run_name,
			"/sandblaster/helpers/extract_sandbox_data.py", 
			"-O", "/test/outputs/sb_profiles", 
			"/test/inputs/sandboxd", ios_version
		])

	subprocess.run([
		"docker", "exec", run_name,
		"mkdir", "/test/outputs/rev_profiles"
	])

	if ios_major_version >= 9:
		subprocess.run([
			"docker", "exec", run_name,
			"sh", "-c", f"cd /sandblaster/reverse-sandbox/ && python2.7 reverse_sandbox.py -r {ios_version} -o /test/outputs/sb_ops -d /test/outputs/rev_profiles/ /test/outputs/sandbox_bundle -psb > /test/outputs/sandbox_profiles.txt"
		])

		subprocess.run([
			"docker", "exec", run_name,
			"sh", "-c", f"cd /sandblaster/reverse-sandbox/ && python2.7 reverse_sandbox.py -r {ios_version} -o /test/outputs/sb_ops -d /test/outputs/rev_profiles/ /test/outputs/sandbox_bundle"
		])
	else:
		subprocess.run([
			"docker", "exec", run_name,
			"sh", "-c",
			f"cd /sandblaster/reverse-sandbox/ && for i in /test/outputs/sb_profiles/*; do python2.7 reverse_sandbox.py -r {ios_version} -o /test/outputs/sb_ops -d /test/outputs/rev_profiles/ \"$i\"; done"
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

	output_dir = pathlib.Path(DIRNAME, test_name, "outputs")
	reference_dir = pathlib.Path(DIRNAME, test_name, "references")

	try:
		compare_directories(output_dir, reference_dir)
	
		print(f"[PASS] {test_name} :)")
	except AssertionError as err:
		print(f"[FAIL] {test_name} - {err}")

	stop_run(run_name)


def main():
	container_name = build_image()

	generic_test(container_name, "iPhone5__1_9.3_13E237", 9, ios_version="9.3")
	
	generic_test(container_name, "iPad2__1_8.4.1_12H321", 8, ios_version="8.4.1", update_refs=True)

	remove_image(container_name)


main()
