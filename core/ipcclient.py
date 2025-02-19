import logging
import sys
import traceback
from core.teamserver import ipc_server
from collections import defaultdict
from multiprocessing import Process, Pipe
from multiprocessing.connection import Client
from threading import Thread

class IPCClient:

    def __init__(self):
        self.subscribers = defaultdict(set)
        self.__conn = None
        self.__thread = None

    @property
    def running(self):
        if self.__thread:
            return self.__thread.is_alive()
        return False

    def run(self):
        return

    def __run(self, pipe):
        self.__conn = Client(ipc_server.address, authkey=ipc_server.authkey)
        try:
            self.run()
        except Exception:
            self.__conn.close()
            #Cause traceback objects aren't pickle'able, whytho.jpg
            pipe.send("".join(traceback.format_exception(*sys.exc_info())))

    def attach(self, event, func):
        self.subscribers[event].add(func)

    def start(self):
        recv_pipe, send_pipe = Pipe()
        self.__thread = Process(target=self.__run, args=(send_pipe,), daemon=True)
        self.__thread.start()
        try:
            if recv_pipe.poll(0.5):
                exc_info = recv_pipe.recv()
                logging.error(f'Error starting process, got exception:\n{exc_info}')
                self.__thread.join()
                raise Exception(exc_info.splitlines()[-1])
        finally:
            recv_pipe.close()
            send_pipe.close()

    def dispatch_event(self, event, msg):
        self.__conn.send((event, msg))
        try:
            data = self.__conn.recv()
            logging.debug(f"Received data back from event: {event} {f'data-len: {len(data)}' if data else ''}")
            return data
        except EOFError:
            pass

    def stop(self):
        self.__thread.kill()
        self.__thread.join()
        logging.debug(f"Stopping process pid: {self.__thread.pid}, name:{self.__thread.name}/{self.__thread.ident}")
