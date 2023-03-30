# Ejercicio 8

Para el ejercicio 8 se opto por usar multiples procesos comunicandose entre si utilizando colas bloqueantes.

La implementacion cuenta con 3 colas: `clients_queue`, `bets_queue`, `waiting_result_queue`. En la primera se van encolando las agencias que quieren enviar apuestas al servidor, en la segunda se encolan los batchs de apuestas de cada agencia para luego ir guardando dichas apuestas, y en la ultima se encolan los clientes que estan esperando por los resultados de los ganadores.

En cuanto a procesos tenemos el main, un pool de workers, un bet writer y un winner definer:

-  El proceso main se encarga de hacer el accept de los clientes y encolarlos en la clients_queue. 
- El pool de workers (la cantidad es configurable, 3 por defecto), procesa por batchs en lugar de procesar por clientes. La idea es que si tengo mas clientes que workers pueda darle lugar a todos y no que uno tenga que esperar a que otro termine para poder enviar apuestas. Por lo tanto, cada worker toma un cliente de la cola y recibe un batch de ese cliente, lee las apuestas y las encola en bets_queue, si dicho batch NO es el ultimo de la agencia, vuelve a encolar esa agencia en la clients_queue y vuelve a repetir el proceso.
- El bet_writer toma de la cola bets_queue un batch de apuestas y las almacena. Si dicho batch es el ultimo de la agencia, encola dicha agencia en la cola de waiting_result_queue.
- El winner definer toma agencias de la waiting_result_queue y recibe los mensajes de solicitud de ganadores. Una vez que todas las agencias solicitaron a los ganadores, envia los mensajes con los resultados (como vimos en el ejercicio 7).

Dado que la seccion critica `store_bets()` solo es accedida por un proceso, no hay problemas de race conditions. Por otro lado, cuando el winner_definer lee del archivo con `load_bets()` ya sabemos que todas las agencias terminaron de mandar y almacenar las apuestas, por lo cual tampoco hay problemas.
