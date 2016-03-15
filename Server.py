# -*- coding: utf-8 -*-

import socket
import sys
import threading
import time
import os

# Server
if len(sys.argv) != 2:
    print("Use : {} <port>".format(sys.argv[0]))
    sys.exit(1)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

BUFFER_SIZE = 20

port = int(sys.argv[1])
sock.bind(('', port))
sock.listen(5)
print("Server running on port {} ...".format(sys.argv[1]))


# Initialisation des users : liste vide
pseudos = threading.Lock()
verif = threading.Condition(pseudos)
users = {}


def write_log(message):
    # Ecriture dans le fichier log
    with open("log.txt", "a") as file:
        temps = time.strftime("[%d/%m/%Y %H:%M:%S]")
        file.write(temps + " : " + message + "\n")


def whitelist_add(user1, user2):
    # Ajout à la liste d'amis
    with verif:
        users[user1]['whitelist'].append(str(user2))
        users[user2]['whitelist'].append(str(user1))


def blacklist_add(pseudo, user):
    # Ajout à la liste d'ignorés
    with verif:
        users[pseudo]['blacklist'].append(str(user))


def session(client, info):

    print(str(info[0]) + " connected")
    write_log(str(info[0]) + " connected")

    global users
    (cli_ip, cli_port) = info
    away = False
    connected = False
    pseudo = ""
    # Traitement du client
    while 1:
        # Lecture de la requete client
        try:
            msg = client.recv(1024).decode()
        except:
            break

        # Interpretation du message
        if msg == "QUIT":
            # Si le client veut se déconnecter
            if len(msg.split()) != 1:
                client.send("301 Usage : /quit".encode())

            with verif:
                del users[pseudo]
            for key in users:
                users[key]['socket'].send("200 {} has left".format(pseudo).encode())
            write_log("{} has left".format(pseudo))

            print(str(info[0]) + " ({}) disconnected".format(pseudo))
            # client.send("200 disconnected from server".encode())
            client.close()
            sys.exit()

        # CONNECT <pseudo> <color>
        elif msg.startswith("CONNECT"):
            liste = msg.split()
            # Connexion au chat
            if len(liste) != 2 and len(liste) != 3:
                client.send("301 Usage : /connect <pseudo> [color]".encode())

            # TODO : Différencier 2 arguments ( sans couleur) et 3 arguments (avec couleur) => couleur 'black' par défaut

            elif not connected:
                if len(liste) == 2:
                    liste.append("black")

                with verif:
                    if liste[1] in users:
                        client.send("503 This pseudo is already taken".encode())
                    else:
                        # Dans l'ordre : {pseudo : ( socket, ip, port, couleur, whitelist, blacklist )}
                        users[liste[1]] = {"socket": client, "ip": cli_ip, "port": cli_port, "color": liste[2], "whitelist": [], "blacklist": []}
                        connected = True
                        pseudo = liste[1]
                        write_log("{0} ({1}) logged in (color : {2})".format(pseudo, info[0], liste[2]))
                        print("{0} ({1}) logged in".format(pseudo, info[0]))
                        for key in users:
                            users[key]['socket'].send("200 {} logged in".format(pseudo).encode())


            else:
                client.send("503 You are already connected".encode())

        # AFK <reason>
        elif msg.startswith("AFK"):
            liste = msg.split(" ", 1)
            if not connected:
                client.send("503 You are not connected".encode())
            else:
                if away:
                    away = False
                    with verif:
                        write_log("{} is no longer afk".format(pseudo))
                    for key in users:
                        users[key]['socket'].send("{} is no longer afk".format(pseudo).encode())

                else:
                    away = True
                    if len(liste) == 1:
                        with verif:
                            write_log("{} is now afk".format(pseudo))
                        for key in users:
                            users[key]['socket'].send("{} is now afk".format(pseudo).encode())
                    else:
                        with verif:
                            write_log("{0} is now afk (reason : {1})".format(pseudo, liste[1]))
                        for key in users:
                            users[key]['socket'].send("{0} is now afk (reason :{1})".format(pseudo, liste[1]).encode())
        # BACK
        elif msg == "BACK":
            if len(msg.split()) != 1:
                client.send("301 Usage : /back".encode())

            elif not connected:
                client.send("503 You are not connected".encode())
            else:
                if away:
                    away = False
                    with verif:
                        write_log("{} is no longer afk".format(pseudo))
                    for key in users:
                        users[key]['socket'].send("{} is back".format(pseudo).encode())
                else:
                    client.send("502 You are not away".encode())

        # RENAME
        elif msg.startswith("RENAME"):
            liste = msg.split()
            if len(msg.split()) != 2:
                client.send("301 Usage : /rename <pseudo>".encode())

            # Si le client n'est pas déjà connecté
            elif not connected:
                client.send("503 You are not connected".encode())
            # Si le client veut se renommer avec un pseudo déjà existant
            else:
                with verif:
                    if liste[1] in users:
                        client.send("503 {} is already taken".format(liste[1]).encode())
                    else:
                        old = users[pseudo]
                        del users[pseudo]
                        users[liste[1]] = old
                        write_log("{0} is now known as {1}".format(pseudo, liste[1]))
                        client.send("200 pseudo successfully changed to {}".format(liste[1]).encode())
                        for key in users:
                            users[key]['socket'].send("200 {0} is now known as {1}".format(pseudo, liste[1]).encode())
                        pseudo = liste[1]

        # HELP
        elif msg == "HELP":
            client.send("200 List of command:\n"
                        "/quit -- Disconnect from the server.\n"
                        "/connect <pseudo> <color> -- Connect to the server. \n"
                        "/rename <pseudo> -- Change your nickname.\n"
                        "/afk <reason> -- Tells everyone you are away.\n"
                        "/back -- Tells everyone you are back.\n"
                        "/list -- List connected users.\n"
                        "/open <pseudo> -- Speak with an user.\n"
                        "/close <pseudo> -- Stop chatting with an user. \n"
                        "/send <pseudo> <file> <port> -- Send a file to an user.\n"
                        "/color <color> -- Change your color.\n"
                        "/ignore <pseudo> -- Blacklist an user.\n"
                        "/pardon <pseudo> -- Unblacklist an user.\n".encode())
        # LIST
        elif msg == "LIST":
            if not connected:
                client.send("503 You are not connected".encode())
            else:
                text = ""
                for key in users:
                    text += key + " > " + str(users[key]['ip']) + ":" + str(users[key]['port']) + " (" + str(users[key]['color']) + ")\n"
                client.send(("200 "+text).encode())

        # SAY <message>
        elif msg.startswith("SAY"):
            text = msg.split(' ', 1)[1]
            if not connected:
                client.send("503 You are not connected".encode())
            else:
                away = False
                ms = "200 {0} : {1}".format(pseudo, text)
                for key in users:
                    if pseudo not in users[key]['blacklist']:
                        users[key]['socket'].send(ms.encode())
                with verif:
                    write_log("200 ({0}) : {1}".format(pseudo, text))

        # COLOR <color>
        elif msg.startswith("COLOR"):
            if not connected:
                client.send("503 You are not connected".encode())

            elif len(msg.split()) != 2:
                client.send("301 Usage : /color <couleur>".encode())

            elif not connected:
                client.send("503 You are not connected".encode())
            else:
                color = msg.split()[1]
                with verif:
                    users[pseudo]['color'] = color
                    write_log("{0} set his color to {1}".format(pseudo, color))
                    client.send("200 color set to {}".format(color).encode())

        # OPEN <pseudo>
        elif msg.startswith("OPEN"):
            if not connected:
                client.send("503 You are not connected".encode())

            elif len(msg.split()) != 2:
                client.send("301 Usage : /open <user>".encode())

            elif msg.split()[1] not in users:
                client.send("404 {} does not exist or is not connected".format(msg.split()[1]).format())

            elif pseudo in users[msg.split()[1]]['blacklist']:
                client.send("504 {} is ignoring you and does not therefore receive your message.".format(msg.split()[1]).encode())

            else:
                user = msg.split()[1]

                if user == pseudo:
                    client.send("503 You can't speak to yourself !".encode())

                elif user in users:
                    users[user]['socket'].send("200 {} wants to chat with you.\nType /yes to accept, /no to decline".format(pseudo).encode())
                    rep = users[user]['socket'].recv(1024).decode()
                    if rep == 'YES':
                        # Ajout whitelist
                        whitelist_add(pseudo, user)
                        with verif:
                            write_log("{0} has started a conversation with {1}".format(pseudo, user))
                        client.send("200 {} agreed to chat with you".format(user).encode())
                        users[user]['socket'].send("200 You agreed to chat with {} !".format(pseudo).encode())
                    elif rep == 'NO':
                        users[user]['socket'].send("200 You denied to chat with {}".format(pseudo).encode())
                        # ne rien faire
                    else:
                        continuer = True
                        while continuer:
                            continuer = False
                            users[user]['socket'].send("200 Type /yes to accept, /no to refuse".encode())
                            rep = users[user]['socket'].recv(1024).decode()
                            if rep == 'YES':
                                # Ajout whitelist
                                whitelist_add(pseudo, user)
                                write_log("{0} has started a conversation with {1}".format(pseudo, user))
                                client.send("200 {} agreed to chat with you".format(user).encode())
                                users[user]['socket'].send("200 You agreed to chat with {} !".format(pseudo).encode())
                            elif rep == 'NO':
                                users[user]['socket'].send("200 You denied to chat with {}".format(pseudo).encode())
                                # ne rien faire
                            else:
                                continuer = True

                else:
                    client.send("404 {} does not exist or is not connected".format(msg.split()[1]).encode())

        # W <user> <message>
        elif msg.startswith("W"):
            if not connected:
                client.send("503 You are not connected".encode())

            elif len(msg.split()) < 3:
                client.send("301 Usage : /w <user> <message>".encode())

            elif msg.split()[1] not in users:
                client.send("404 {} does not exist or is not connected".format(msg.split()[1]).encode())

            elif msg.split()[1] in users[pseudo]['blacklist']:
                client.send("504 {} is ignoring you and does not therefore receive your message.".format(msg.split()[1]).encode())

            elif msg.split()[1] not in users[pseudo]['whitelist']:
                client.send("503 You should ask {0} to talk with you using the /open {0} command".format(msg.split()[1]).encode())

            else:
                msg = msg.split(' ', 3)
                user = msg[1]
                message = msg[2]
                users[user]['socket'].send("200 de {0} : {1}".format(pseudo, message).encode())
                client.send("200 à {0} : {1}".format(user, message).encode())
                write_log("{0} -> {1} : {2}".format(pseudo, user, message))

        # IGNORE <user>
        elif msg.startswith("IGNORE"):
            if not connected:
                client.send("503 You are not connected".encode())

            elif len(msg.split()) != 2:
                client.send("301 Usage : /ignore <user>".encode())

            elif msg.split()[1] == pseudo:
                client.send("503 You can't be ignoring yourself !".encode())

            elif msg.split()[1] in users[pseudo]['blacklist']:
                client.send("302 You are already ignoring {} !".format(msg.split()[1]).encode())

            else:
                user = msg.split()[1]
                blacklist_add(pseudo, user)
                client.send("200 You are now ignoring {}".format(user).encode())
                with verif:
                    write_log("{0} a ignoré {1}".format(pseudo, user))

        # PARDON <user>
        elif msg.startswith("PARDON"):
            if not connected:
                client.send("503 You are not connected".encode())

            elif len(msg.split()) != 2:
                client.send("301 Usage : /pardon <user>".encode())

            elif msg.split()[1] not in users[pseudo]['blacklist']:
                client.send("403 {} was already not ignored".format(msg.split()[1]).encode())

        # SEND <file> <user>
        elif msg.startswith("SEND"):
            if not connected:
                client.send("503 You are not connected".encode())

            elif len(msg.split()) != 4:
                client.send("301 Usage : /send <user> <filepath> <port>")

            elif msg.split()[1] == pseudo:
                client.send("503 You can't send a file to yourself !".encode())

            elif msg.split()[2] not in users:
                client.send("404 {} is not connected or does not exist".format(msg.split()[1]).encode())

            elif pseudo in users[msg.split()[2]]['blacklist']:
                client.send("503 {} ignores you".format(msg.split()[2]).encode())

            elif msg.split()[3] == sys.argv[1]:
                client.send("503 port must be different from {}".format(sys.argv[1]).encode())

            else:
                user = msg.split()[1]
                file = msg.split()[2]
                port = msg.split()[3]

                users[user]['socket'].send("{0} wants to send you a file : {1}\nType /yes to accept, /no to decline".format(pseudo, file, taille).encode())

                rep = users[user]['socket'].recv(1024).decode()
                retry = True
                while retry:
                    retry = False
                    if rep == "NO":
                        # Si l'user refuse
                        client.send("{} has declined file sending.".format(user).encode())
                        users[user]['socket'].send("200 You have declined file reception.".encode())

                    elif rep == "YES":
                        # Si l'user accepte
                        my_ip = str(info[0])
                        dest_ip = str(users[user]['ip'])

                        # Envoi de l'ip source au destinataire pour créer le socket
                        users[user]['socket'].send("100 P2P_RECEP {0} {0}".format(my_ip, port).encode())
                        client.send("100 P2P_SEND {0} {1} {2}".format(file, dest_ip, port))

                        with verif:
                            write_log("{0} has send '{1}' to {2}".format(pseudo, file, user))

                    else:
                        users[user]['socket'].send("501 type /yes to accept, /no to decline".encode())
                        retry = True

        # Commande non reconnue
        else:
            client.send("404 This command does not exist.\nType /help for command list".encode())

write_log("Server running on port {} ...".format(sys.argv[1]))

while True:
    # Exécution du serveur
    (client_connect, infos) = sock.accept()
    t = threading.Thread(target=session, args=(client_connect, infos))
    t.start()
    t.join()
