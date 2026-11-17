# Provedor OpenAI opcional na ANI

Integração híbrida: mantém os provedores/modelos existentes e permite usar a API OpenAI como complemento no endpoint `POST /v1/chat/completions`.

## Configuração (somente no servidor)
```env
ANI_OPENAI_ENABLED=false
ANI_OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=
```
Após resgatar o cupom no painel OpenAI e configurar a chave no gerenciador de segredos do deploy, altere `ANI_OPENAI_ENABLED=true` para ativar. Não registre a chave no GitHub, frontend ou logs.

A pesquisa Wikipedia mantém prioridade quando acionada. Se a OpenAI estiver indisponível, o fluxo atual da ANI permanece como fallback. O campo `custo` é mantido em 0.0 por compatibilidade e **não representa o custo real da API**; consulte Usage/Billing na OpenAI. Configure limites e alertas no painel da OpenAI, pois este PR não implementa teto financeiro rígido nem consulta saldo promocional.

## Teste
1. Sem chave e com `ANI_OPENAI_ENABLED=false`, confirme que o chat anterior permanece funcional.
2. Com chave em ambiente seguro, habilite o provedor e envie uma mensagem de teste.
3. Confirme `model: ani+openai/...` e `tokens_usados` na resposta.
4. Desative a flag para voltar ao comportamento anterior.
