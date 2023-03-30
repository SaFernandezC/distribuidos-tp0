# Ejercicio 6

No hay modificaciones muy grandes con respecto al ejercicio anterior.

Ahora cuando el cliente quiere enviar un mensaje que contiene parte de las apuestas (batch), envia al protocolo el numero de agencia, un vector de apuestas, y un indicador sobre si dicho mensaje es el ultimo batch o no. Ejemplo, se crea el siguiente mensaje:

`{"agency":1, "data":["apuesta1","apuesta2",...,"apuestaN"], "last_batch": False}`

Utilizando json.dumps() se transforma dicho diccionario en string, se envia como bytes mediante el protocolo y cuando el servidor lo recibe vuelve a armar el diccionario con json.loads().

Dado que el mensaje recibido por el servidor indica si es el ultimo batch o no, este sabe si seguir esperando por mas mensajes o si ya finalizo la tarea. Si puede almacenar todas las apuestas de forma correcta, envia el ACK al cliente.

La cantidad de apuestas por batch se puede configurar desde el archivo `config.ini` en la carpeta del cliente, por defecto `BETS_PER_BATCH=2000`
