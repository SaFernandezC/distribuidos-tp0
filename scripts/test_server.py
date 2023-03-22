import subprocess

TEST_STR = "Testing server!"

result = subprocess.run(
    ["docker", "run", "--rm", "--network=tp0_testing_net", "--entrypoint=sh","subfuzion/netcat", "-c", "echo "+TEST_STR+" | nc server 12345"],
    capture_output=True, text=True
)

# Me retorna un /n por eso el strip
parsed_result = result.stdout.strip()

if parsed_result == TEST_STR:
    print(f"Funcionamiento correcto: envio {TEST_STR} y recibo {parsed_result}")
else:
    print(f"Funcionamiento incorrecto: envio {TEST_STR} y recibo {parsed_result}")