from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import pytz
import re
import psycopg2
import decimal
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urlparse, parse_qs

class APIServer(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.conexion = None

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', 'https://stellular-fox-1c153b.netlify.app')
        #self.send_header('Access-Control-Allow-Origin', 'http://localhost:4200')
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
                host='oregon-postgres.render.com',
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
                altitud_mar = data.get('altitud_mar')
                nodo = data.get('nodo')
                print(nodo)
                print(altitud_mar)
                #fe_creacion = datetime.now()
                zona_horaria = pytz.timezone("America/Guayaquil")
                fe_creacion = datetime.now().astimezone(zona_horaria)
                cursor.execute("INSERT INTO data_calidad (monoxido_carbono, humedad, temperatura, dioxido_carbono, altura_nivel_mar, gas_propano, nodo) VALUES (%s,%s,%s,%s,%s,%s,%s)", (monoxido_carbono, humedad, temperatura, dioxido_carbono, altitud_mar, gas_propano, nodo))
                print(fe_creacion)
                conn.commit()
                
                cursor.close()
                self.desconectar_bd()
                print(monoxido_carbono)
               
                if int(monoxido_carbono) > 150:
                    self.enviar_correo_alerta(temperatura, monoxido_carbono, humedad, dioxido_carbono, gas_propano)
                elif int (dioxido_carbono) > 150:
                    self.enviar_correo_alerta(temperatura, monoxido_carbono, humedad, dioxido_carbono, gas_propano)
                    
                # Configurar las cabeceras de respuesta
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                # Construir la respuesta JSON
                response = {'status': 'OK', 'data_received': temperatura}
                json_response = json.dumps(response)
                print("Llega ingresa")
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
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/obtener_registro':
            try:
                query_params = parse_qs(parsed_url.query)
                nodo = query_params.get('nodo', [None])[0]
                conn = self.conectar_bd()
                cursor = conn.cursor()

                # Consulta para obtener el último registro ingresado
                cursor.execute("SELECT * FROM data_calidad where nodo = "+nodo+" order by id desc LIMIT 1")
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
                        'altitud_mar': registro[4],
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

        elif path == '/obtener_registros_hoy':
            try:
                query_params = parse_qs(parsed_url.query)
                nodo = query_params.get('nodo', [None])[0]
                fe_inicio = query_params.get('fe_inicio', [None])[0]
                fe_fin = query_params.get('fe_fin', [None])[0]

                conn = self.conectar_bd()
                cursor = conn.cursor()

                #zona_horaria = pytz.timezone("America/Guayaquil")
                #fe_creacion = datetime.now().astimezone(zona_horaria)
                
                # Consulta para obtener el último registro ingresado
                cursor.execute("select humedad, gas_propano, monoxido_carbono, TIMEZONE('America/Guayaquil', fe_creacion), dioxido_carbono from data_calidad WHERE date(TIMEZONE('America/Guayaquil', fe_creacion)) between %s and %s and nodo = %s order by fe_creacion asc;", (fe_inicio, fe_fin, nodo))
                #cursor.execute("SELECT date(TIMEZONE('America/Guayaquil', CURRENT_DATE));")
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
                            
                            'propano' : registro_list[1],
                            'monoxido_carbono' : registro_list[2],
                            'fe_creacion': registro_list[3].strftime("%Y-%m-%d %H:%M:%S"),  # Formatear la fecha
                            'dioxido_carbono' : registro_list[4]
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

        elif path == '/obtener_altura':
            try:
                conn = self.conectar_bd()
                cursor = conn.cursor()
                
                cursor.execute("select ((select COALESCE(altura_nivel_mar, 0) from data_calidad where nodo = 1 order by id desc LIMIT 1) + (select COALESCE(altura_nivel_mar, 0) from data_calidad where nodo = 2 order by id desc LIMIT 1)) / 2;")
                registros = cursor.fetchall()

                if registros:
                    response = []
                    for registro in registros:
                        # Convertir campos decimales a flotantes si es necesario
                        registro_list = list(registro)
                        for i in range(len(registro_list)):
                            if isinstance(registro_list[i], decimal.Decimal):
                                registro_list[i] = float(registro_list[i])

                        # Construir la respuesta JSON para cada registro
                        registro_json = {
                            'altura': registro_list[0]
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
                # Manejo de errores con cabeceras correctamente configuradas
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')  # Asegúrate de usar 'Content-Type'
                self.end_headers()  # Cierre correcto de las cabeceras
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        else:
            # Respuesta para ruta no permitida con cabeceras bien formadas
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')  # Asegúrate de usar 'Content-Type'
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Acceso denegado'}).encode('utf-8'))

    def enviar_correo_alerta(self, temperatura, monoxido_carbono, humedad, dioxido_carbono, gas_propano):
        print("llega")
        
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
        #message['To'] = 'wperezg@uteq.edu.ec, fotospriv21@gmail.com'
        message['Subject'] = 'UTEQ: SISTEMA DE MONITOREO DE CALIDAD DE AIRE'

        # Cuerpo del correo electrónico
        body = f'Se ha superado los límite permitido de la medición de monoxido de carbono:{monoxido_carbono}\n\n'
        body += f'Temperatura: {temperatura}\n'
        body += f'Monóxido de carbono: {monoxido_carbono}\n'
        body += f'Humedad: {humedad}\n'
        body += f'Dióxido de carbono: {dioxido_carbono}\n'
        message.attach(MIMEText(body, 'plain'))

            
        # Inicia una conexión SMTP segura con el servidor de Gmail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("llega2")
            server.starttls()  # Inicia una conexión segura
            server.login(sender_email, password)  # Inicia sesión en la cuenta de Gmail
            
            #for correo in correos:
             #   message['To'] = correo
            text = message.as_string()
            server.sendmail(sender_email, correos, text)  # Envía el correo electrónico
            print("Enviado exitosamente")

      

def run_server(port=8000):
    # Crea una instancia del servidor y especifica el puerto
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIServer)
    print('Servidor en ejecución en el puerto', port)

    # Ejecuta el servidor
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
