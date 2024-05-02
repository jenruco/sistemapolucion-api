from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import psycopg2
import decimal
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

class APIServer(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.conexion = None

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', 'http://localhost:4200')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        BaseHTTPRequestHandler.end_headers(self)

    #def do_OPTIONS(self):
    #    self.send_response(200)
    #    self.end_headers()
    
    def conectar_bd(self):
        try:
            self.conexion = psycopg2.connect(
                dbname='calidad_data',
                user='calidad_data_user',
                password='eCPQP0qGUi7rjax6TDxftu76u1JfZSdH',
                host='dpg-copvq0q1hbls73dn7o3g-a',
                port='5432'
            )
            return self.conexion
        except psycopg2.Error as e:
            print("Error al conectar a la base de datos:", e)

    def desconectar_bd(self):
        if self.conexion is not None:
            self.conexion.close()

    def do_POST(self):
        if re.search('/ingresa', self.path):
            # Leer los datos JSON de la solicitud
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
            except ValueError as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'JSON inválido'}).encode('utf-8'))
                return
            
            try:
                conn = self.conectar_bd()
                cursor = conn.cursor()
                
                temperatura = data.get('temperatura')
                monoxido_carbono = data.get('monoxido_carbono')
                humedad = data.get('humedad')
                dioxido_carbono = data.get('dioxido_carbono')
                gas_propano = data.get('gas_propano')
                fe_creacion = datetime.now()
                cursor.execute("INSERT INTO data_calidad (monoxido_carbono, humedad, temperatura, dioxido_carbono, presion_admosferica, fe_creacion, gas_propano) VALUES (%s,%s,%s,%s,%s,%s,%s)", (monoxido_carbono, humedad, temperatura, dioxido_carbono, 0, fe_creacion, gas_propano))
                
                conn.commit()
                
                cursor.close()
                self.desconectar_bd()
                          
                #if int(monoxido_carbono) > 200:
                    #self.enviar_correo_alerta(temperatura, monoxido_carbono, humedad, dioxido_carbono)
                #elif int (dioxido_carbono) > 600:
                    #self.enviar_correo_alerta(temperatura, monoxido_carbono, humedad, dioxido_carbono)
                    
                # Configurar las cabeceras de respuesta
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                # Construir la respuesta JSON
                response = {'status': 'OK', 'data_received': temperatura}
                json_response = json.dumps(response)

                # Enviar la respuesta
                self.wfile.write(json_response.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(403)

    def do_GET(self):
        if self.path == '/obtener_registro':
            try:
                conn = self.conectar_bd()
                cursor = conn.cursor()

                # Consulta para obtener el último registro ingresado
                cursor.execute("SELECT * FROM data_calidad order by id desc LIMIT 1")
                registro = cursor.fetchone()
                if registro:
                    registro = list(registro)
                    for i in range(len(registro)):
                        if isinstance(registro[i], decimal.Decimal):
                            registro[i] = float(registro[i])
                    # Construir la respuesta JSON
                    response = {
                        #'id': registro[0],
                        'monoxido_carbono': registro[0],
                        'humedad': registro[1],
                        'dioxido_carbono': registro[2],
                        'temperatura': registro[3],
                        'presion_admosferica': registro[4],
                        'gas_propano': registro[7]
                        
                    }
                    json_response = json.dumps(response)

                    # Configurar las cabeceras de respuesta
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()

                    # Enviar la respuesta
                    self.wfile.write(json_response.encode('utf-8'))
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No se encontraron registros'}).encode('utf-8'))

                cursor.close()
                self.desconectar_bd()
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        elif self.path == '/obtener_registros_hoy':
            try:
                conn = self.conectar_bd()
                cursor = conn.cursor()

                # Consulta para obtener el último registro ingresado
                cursor.execute("select humedad, temperatura, monoxido_carbono, fe_creacion from data_calidad WHERE fe_creacion::date = CURRENT_DATE order by fe_creacion asc;")
                registros = cursor.fetchall()

                if registros:
                    # Convertir los registros a formato JSON
                    response = []
                    for registro in registros:
                        # Convertir campos decimales a flotantes si es necesario
                        registro_list = list(registro)
                        for i in range(len(registro_list)):
                            if isinstance(registro_list[i], decimal.Decimal):
                                registro_list[i] = float(registro_list[i])

                        # Construir la respuesta JSON para cada registro
                        registro_json = {
                            'humedad': registro_list[0],
                            'temperatura': registro_list[1],
                            'monoxido_carbono' : registro_list[2],
                            'fe_creacion': registro_list[3].strftime("%Y-%m-%d %H:%M:%S")  # Formatear la fecha
                        }
                        response.append(registro_json)

                    # Configurar las cabeceras de respuesta
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()

                    # Enviar la respuesta
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No se encontraron registros'}).encode('utf-8'))

                cursor.close()
                self.desconectar_bd()
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(403)

    def enviar_correo_alerta(self, temperatura, monoxido_carbono, humedad, dioxido_carbono):
        # Configura los parámetros del servidor SMTP de Gmail
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587  # Puerto TLS para Gmail
        sender_email = 'wilsonperezgarcia2000@gmail.com'
        password = 'prak rdzd jzcr abwb'

        # Configura el destinatario del correo electrónico
        # recipient_email = 'wperezg@uteq.edu.ec, fotospriv21@gmail.com'
        correos = ['wperezg@uteq.edu.ec', 'henry_5198@hotmail.com']
        # Crea el objeto del mensaje
        message = MIMEMultipart()
        message['From'] = 'wilsonperezgarcia2000@gmail.com'
        message['To'] = ', '.join(correos)  # Concatena las direcciones de correo con comas
#        message['To'] = 'wperezg@uteq.edu.ec, fotospriv21@gail.com'
        message['Subject'] = 'Alerta: Se ha superado el límite de gases'

        # Cuerpo del correo electrónico
        body = f'Se ha detectado la superación del límite permitido de la medición de CO.\n\n'
        body += f'Temperatura: {temperatura}\n'
        body += f'Monóxido de carbono: {monoxido_carbono}\n'
        body += f'Humedad: {humedad}\n'
        body += f'Dióxido de carbono: {dioxido_carbono}\n'
        message.attach(MIMEText(body, 'plain'))
       
        # Inicia una conexión SMTP segura con el servidor de Gmail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Inicia una conexión segura
            server.login(sender_email, password)  # Inicia sesión en la cuenta de Gmail
            
            #for correo in correos:
             #   message['To'] = correo
            text = message.as_string()
            server.sendmail(sender_email, correos, text)  # Envía el correo electrónico
            #print("Correo electrónico de alerta enviado exitosamente a", join(correos))

    
    

def run_server(port=8000):
    # Crea una instancia del servidor y especifica el puerto
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIServer)
    print('Servidor en ejecución en el puerto', port)

    # Ejecuta el servidor
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
