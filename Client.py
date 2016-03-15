# -*- coding: utf-8 -*-

import socket
import sys
import threading
import os

# Client
if len(sys.argv) != 3:
    print("Use : {} <ip_address> <port>".format(sys.argv[0]))
    sys.exit(1)

try:
    connec = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connec.connect((sys.argv[1], int(sys.argv[2])))
except:
    print("Server is offline.")
    sys.exit(1)


# Définition des threads clientss
def envoi(connexion):
    while True:
        message = input()

        if len(message.split()) == 1:

            if message.startswith("/"):
                message = message[1:len(message)].upper()

            else:
                message = "SAY " + message

        else:
            if message.startswith("/"):
                message = message[1:len(message)]
                com = message.split(' ', 1)[0].upper()
                texte = message.split(' ', 1)[1]

                message = com + " " + texte

            else:
                message = "SAY " + message

        # Cas d'un fichier
        if message.startswith("SEND"):
            if len(message.split()) == 4:
                file = message.split()[2]

                try:
                    with open(file, "rb"):
                        # Le fichier existe
                        cmd = message.encode()
                        try:
                            connexion.send(cmd)
                        except:
                            sys.exit()
                except:
                    print("Le fichier {} n'existe pas ou n'est pas accessible".format(file))

            else:
                print("Usage : /send <user> <filepath> <port>")

        else:
            cmd = message.encode()
            try:
                connexion.send(cmd)
            except:
                sys.exit()

            if message == "QUIT":
                connexion.close()
                sys.exit()


def recep(connexion):
    while True:
        try:
            resp = connexion.recv(1024).decode()
        except Exception as e:
            print("Disconnected from the server")
            sys.exit()

        if resp == "200 disconnected from server":
            connexion.shutdown(socket.SHUT_RDWR)
            connexion.close()
            sys.exit()

        elif resp.startswith("100 P2P_SEND"):
            file = resp.split()[2]
            ip = resp.split()[3]
            port = resp.split()[4]

            threading.Thread(target=envoi_fichier, args=(file, ip, port)).start().join()

        elif resp.startswith("100 P2P_RECEP"):
            file = resp.split()[2]
            ip = resp.split()[3]
            port = resp.split()[4]

            threading.Thread(target=recep_fichier, args=(file, ip, port)).start().join()

        else:
            print(resp.split(" ", 1)[1])


def envoi_fichier(file, ip, port):

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            f = open(file, "rb")
            taille = os.path.getsize(f)

            print("Envoi du fichier '{}' en cours...".format(file))

            if taille > 1024:
                num = 0
                for i in range(taille/1024):
                    f.seek(num, 0)
                    datas = f.read(1024)
                    sock.sendto(datas, (ip, port))
                    num += 1024
            else:
                datas = f.read()
                sock.sendto(datas, (ip, port))

            sock.sendto("100 OK".encode(), (ip, port))
            f.close()
        except:
            print("Erreur à l'envoi")


def recep_fichier(file, ip, port):

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

        sock.bind((ip, port))

        try:
            f = open(file, "wb")

            pas_fini = True
            while pas_fini:
                contenu = sock.recv(1024)
                if contenu.decode() != "100 OK":
                    f.write(contenu)
                else:
                    f.close()
                    print("Fichier {} reçu !".format(file))

        except:
            print("Erreur à la réception")


"""def envoi(connexion):
    while True:
        msg = input()
        connexion.send(msg.encode())

def recep(connexion):
    while True:
        msg = connexion.recv(1024)
        print(msg.decode())"""

# Main
sendv = threading.Thread(target=envoi, args=(connec,))
sendv.start()

recepv = threading.Thread(target=recep, args=(connec,))
recepv.start()

sendv.join()
recepv.join()
