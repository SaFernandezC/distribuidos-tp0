# Ejercicio 5

Para la ejecucion cada cliente debe recibir por variables de entorno los diferentes parametros que lo identifican, junto con su numero de apuesta (Ver el docker-compose).

---

Para la solucion del ejercicio 5 se opto por crear una clase Protocolo y una clase Socket, ambas utilizadas tanto por el servidor como por los clientes para tener una mayor abstraccion en cuanto a la comunicacion.

La clase Socket es simplemente un wrapper de un socket TCP el cual brinda todas las funciones basicas de un socket pero modifica el `send()` y  `recv()` para evitar los fenomenos de short read y short write.

El funcionamiento del protocolo en si es sencillo, consta de los siguientes pasos cuando se quiere enviar un mensaje:

1. Cliente envia un mensaje de 4 bytes (configurable) en donde indica la longitud que tendra el proximo mensaje con la apuesta
2. Cliente envia la apuesta y espera ACK
3. El servidor recibe el primer mensaje con la longitud del proximo mensaje
4. Recive el mensaje de la apuesta leyendo tantos bytes como indicaba el mensaje anterior
5. Servidor enviar mensaje de 4 bytes con ACK

El protocolo funciona enviando y reciviendo bytes.

Por dentro el protocolo tambien se asegura de no enviar paquetes mayores a 8kb, si el usuario envia un mensaje mayor a dicho tamaño el protocolo se encargara de dividirlo en paquetes mas pequeños y enviar todos de forma correcta.
