# Ejercicio 7

Dado que en el ejercicio 6 los batchs que el cliente envia ya indican si es el ultimo o no, fue mas sencillo resolver este ejercicio.

Una vez que el cliente termina de leer y enviar las apuestas de su archivo de apuestas, llama a una funcion que pide por los ganadores. Dicha funcion se comunica con el protocolo, quien envia un mensaje al servidor, en esta parte el protocolo funciona enviando un mensaje de 4 bytes con el id de la agencia al servidor y queda esperando por una respuesta, que contendra a los ganadores.

El servidor no enviara una respuesta hasta que todas las agencias hayan mandado todas sus apuestas, se opto por esta solucion en lugar de un polling constante al servidor ya que al ser pocos clientes y pocos datos no es mucho el tiempo que los clientes deben esperar (se podria haber considerado algun algoritmo de poll y sleep hasta que eventualmente el servidor responde, de esta forma no "bloqueamos" al cliente).

Por el lado del servidor, una vez que recibe el ultimo batch espera un mensaje con el id de la agencia indicando que dicha agencia esta pidiendo los ganadores. Cuando todas las agencias terminan de enviar sus datos el servidor realiza el "sorteo" y guarda los ganadores por agencia. El siguiente paso es enviar a cada agencia los ganadores del "sorteo", para esto utiliza el protocolo de igual forma que en el ejercicio 5: primero un mensaje de 4 bytes indicando el largo del mensaje a enviar y luego envia efectivamente los datos.

Si se cambia la cantidad de agencias cliente se debe cambiar la variable `NUMBER_OF_CLIENTS` en config.ini del servidor.
