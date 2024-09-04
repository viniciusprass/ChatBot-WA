import json
import requests
from datetime import datetime
import boto3
import ast

# Configuração da API OpenAI e WhatsApp
api_key_gpt = 'GPT KEY'
api_key_wpp = 'WHATSAPP KEY'

dynamodb = boto3.resource('dynamodb')
table_context = dynamodb.Table('context')
table_appointments = dynamodb.Table('appointments')

def sendMessage(message, number):
    url = "https://graph.facebook.com/v20.0/418875104636202/messages"
    
    headers = {
        'Authorization': f'Bearer {api_key_wpp}',
        'Content-Type': 'application/json'
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": number,  
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    return response

def assistMessage(messages):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key_gpt}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return

def lambda_handler(event, context):

    http_method = event.get('requestContext', {}).get('httpMethod')
    body = json.loads(event.get('body', '{}'))

    if not http_method:
        return {
            'statusCode': 400,
            'body': 'Método HTTP não especificado.'
        }
    
    if http_method == 'GET':
        query_params = event.get('queryStringParameters', {})
        if query_params.get('hub.mode') == 'subscribe' and query_params.get('hub.verify_token') == 'verify-code':
            return {
                'statusCode': 200,
                'body': query_params.get('hub.challenge', '')
            }
        return {
            'statusCode': 403,
            'body': 'Token de verificação inválido'
        }

    if http_method == 'POST':
        entries = body.get('entry', [])
        if entries:
            changes = entries[0].get('changes', [])
            if changes:
                value = changes[0].get('value', {})
                messages = value.get('messages', [])
                if messages:
                    message = messages[0]
                    sender = message.get('from', 'Sem remetente')
                    user_message = message.get('text', {}).get('body', 'Sem texto')
                    if user_message:
                        context_data = table_context.get_item(Key={'id': sender})
                        conversation_history = context_data.get('Item', {}).get('conversation_history', [])
    
                        conversation_history.append({"role": "user", "content": user_message})
                        
                        assistantName = 'Assistente Inteligente WA'
                        today = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        mensagens = [
                            {
                                "role": "system",
                                "content": f"Este é o histórico das conversas anteriores: {conversation_history}. Você irá atender os clientes da WA Mobile Oil Change. Apresente-se como {assistantName}. A empresa consiste em uma van que vai até o cliente, sem custos de deslocamento para ele. Os serviços oferecidos são: troca de óleo, troca de filtro de ar, troca de filtro de óleo, troca de fluido de arrefecimento, troca de pastilhas de freio, troca de limpadores de para-brisa e troca de bateria. Na troca de óleo, o cliente ganha gratuitamente: troca do fluido de arrefecimento e troca do líquido do limpador de para-brisa, junto com a revisão dos limpadores, revisão dos pneus, revisão da bateria e revisão das pastilhas de freio. Os agendamentos são feitos de segunda a sábado, 24 horas por dia, no fuso horário da Flórida. Os valores da troca de óleo são calculados por QTZ e têm duas variações de valores, uma para carros de uso doméstico e outra para frotas. Os valores da troca de óleo para uso doméstico são os seguintes: 5QTZ = USD75, 6QTZ = USD80, 7QTZ = USD85, 8QTZ = USD93, DIESEL 13QTZ = USD138. Para frotas, os valores da troca de óleo são: 5QTZ = USD60, 6QTZ = USD68, 7QTZ = USD75, 8QTZ = USD83, DIESEL 13QTZ = USD128. Os valores dos serviços adicionais não diferem entre uso doméstico e frotas, sendo: Filtro de ar = USD20, bateria = USD60, troca de limpadores de para-brisa = USD10, troca de pneu furado = USD30, rotação de pneus = USD40, troca de pastilhas de freio (dianteira ou traseira) = USD70, troca de pastilhas de freio (dianteira e traseira) = USD140. Para realizar o agendamento, você precisa perguntar ao cliente: nome, endereço onde o serviço será realizado (peça rua, bairro e cidade, se o endereço fornecido for fora de Orlando, informe que não atendemos lá, só aceite bairros válidos), modelo do carro em que o serviço será feito, dia e hora do agendamento, e se o serviço será para carro de uso doméstico ou para frotas (TODAS as informações são obrigatórias). Com base no modelo do carro, o assistente deve automaticamente calcular e informar o valor da troca de óleo, conforme os valores de QTZ especificados acima. Considere que hoje é o dia: {today}. Atendemos apenas nos bairros de Orlando, Flórida. Quando o cliente fornecer o modelo do carro, o assistente deve verificar quantos QTZ são necessários e responder com o valor correspondente. A WA trabalha com óleo totalmente sintético. Após coletar as informações, informe ao cliente as informações coletadas, o valor do serviço e peça para ele digitar 'ok', para confirmar as informações. Não responda nada além de dúvidas sobre serviços mecânicos e sobre nossa empresa"
                            },
                            {"role": "user", "content": user_message}
                        ]
                        
                        def collectingData():
                            mensagens.append({
                                "role": "system", 
                                "content": f"Caso tenha sido enviada para confirmação a visita, me retorne os dados informados neste formato: {{'servico': a, 'nome': x, 'modelo': z, 'uso': a, 'localizacao': b, 'data': 'dia/mes/ano hora', 'code':'gere um código de 6 digitos aleatórios'}}. Onde 'modelo' é o modelo do carro, o 'uso' é se é domestico ou de frota e o 'servico' é o serviço a ser prestado(exemplo: 'troca de oleo'), mande apenas o dicionário limpo, sem mais informações. Se não conseguir coletar, retorne 'Unconfirmed'"
                            })
                        
                            data = assistMessage(mensagens)
                            
                            print(f'Dados: {data}')
                            
                            if data == 'unconfirmed':
                                return
                            
                            try:
                                dictionaryData = ast.literal_eval(data)
                            except (ValueError, SyntaxError):
                                sendMessage(f'Seu código de agendamento é: {code}. \n\nA solicitação de agendamento foi enviada para aprovação e você receberá a confirmação em breve. \n\nSe precisar de mais alguma coisa, estarei à disposição!', sender)
                                return
                            
                            code = dictionaryData['code']
                            table_appointments.put_item(
                                Item={
                                    'id': code,  # Incluindo a chave primária como 'id'
                                    'servico': dictionaryData['servico'],
                                    'nome': dictionaryData['nome'],
                                    'telefone': sender,
                                    'modelo': dictionaryData['modelo'],
                                    'uso': dictionaryData['uso'],
                                    'localizacao': dictionaryData['localizacao'],
                                    'data': dictionaryData['data']
                                }
                            )
                            sendMessage(f'Seu código de agendamento é: {code}. \n\nA solicitação de agendamento foi enviada para aprovação e você receberá a confirmação em breve. \n\nSe precisar de mais alguma coisa, estarei à disposição!', sender)

                        if user_message.lower() == 'ok':
                            collectingData()
                            table_context.delete_item(Key={'id': sender})
                            
                        else:
                            resposta = assistMessage(mensagens)
                            
                            conversation_history.append({"role": "assistant", "content": resposta})
                            table_context.put_item(
                                Item={
                                    'id': sender,
                                    'conversation_history': conversation_history
                                }
                            )
                            
                            sendMessage(resposta, sender)

                        return {
                            'statusCode': 200,
                        }
                                              
                else:
                    print("Nenhuma mensagem encontrada no corpo do evento.")

        return {
            'statusCode': 400,
            'body': 'Evento POST malformado.'
        }

    return {
        'statusCode': 405,
        'body': json.dumps({'message': 'Method not allowed'})
    }
