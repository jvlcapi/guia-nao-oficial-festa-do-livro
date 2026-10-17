# Plano de implementação

Objetivo: gerar o catálogo da Festa do Livro da USP a partir de qualquer edição (sem link fixo no código), publicar esse catálogo numa página com listas pessoais e privadas, e deixar tudo pronto para o dia em que a lista da próxima edição sair.

## Etapa 1: Coletor configurável por edição
**Goal**: código que descobre a edição (automática pela página inicial do site, ou fixada em `settings.json`), lista as editoras pela API e baixa os PDFs de preço.
**Success Criteria**: `python -m festa_do_livro download` com `"edition": "auto"` encontra `27-festa-do-livro-da-usp` hoje; trocar para outra edição é mudar uma linha.
**Tests**: detecção da edição a partir de HTML salvo; leitura de `settings.json` (auto e fixa); paginação da API de editoras com respostas salvas; edição inexistente gera erro claro.
**Status**: Complete

## Etapa 2: Leitura dos PDFs, conferência e catálogo
**Goal**: portar o leitor validado (tabelas + posição do texto), a conferência de preços e a montagem do `catalogo.json` com os dados do evento (nome, datas).
**Success Criteria**: rodar sobre os PDFs da 27ª edição reproduz o catálogo já validado (34.771 livros) e o relatório aponta só as divergências conhecidas.
**Tests**: regressões reais com PDFs de amostra (HarperCollins "Mesa" lida como preço, Atma, Contraponto só com %, Ars et Vita com capa inteira); URLs com token removidas; preço abaixo de R$ 1 descartado.
**Status**: Complete

## Etapa 3: GitHub Action e segredos
**Goal**: workflow que roda sob demanda e diariamente, gera catálogo + relatório e faz commit só quando algo mudou.
**Success Criteria**: execução manual no GitHub termina verde e gera `data/<edição>/catalogo.json`; nenhuma chave no repositório (só `GITHUB_TOKEN` automático; futuras chaves via Actions secrets).
**Tests**: execução manual do workflow; checagem de que `.env` e caches estão no `.gitignore`.
**Status**: Complete

## Etapa 4: Site público com listas no aparelho
**Goal**: site estático no GitHub Pages, aberto a qualquer pessoa sem conta nem convite, que lê nome/datas da edição e o catálogo publicados junto, guarda a lista no navegador por edição, compartilha a lista por link e funciona sem internet depois da primeira visita. (Substitui a página no Claude Artifact, que exigia conta no claude.ai e convite de Colaborador.)
**Success Criteria**: o workflow publica o site com o catálogo da 27ª edição; no site publicado dá para buscar, adicionar, remover, definir orçamento, gerar o link e abrir o link em outro navegador com os mesmos livros.
**Tests**: montagem do site com a edição atual (`tests/test_site_assembly.py`); checagem de sintaxe do script; teste manual no endereço publicado.
**Status**: Complete (falta só um teste num celular de verdade, issue #16)

## Etapa 5: Roteiro do dia do lançamento
**Goal**: README com o passo a passo para quando a nova edição sair (detectar, rodar, conferir relatório, publicar) e liberação do repositório como público.
**Success Criteria**: dá para seguir o roteiro sem consultar o histórico da conversa.
**Tests**: ensaio do roteiro com a 27ª edição fixada em `settings.json`.
**Status**: In Progress (README pronto; falta o dia do lançamento)

## Etapa 6: Catálogo sem livros perdidos nem preços trocados
**Goal**: corrigir o que a revisão de outubro de 2026 achou nos dados: ISBN com dígito verificador inválido ou quebrado em duas linhas, livros descartados por repetir ISBN, o mesmo ISBN em duas editoras, preço de capa publicado como preço de feira, links que não levam ao livro, sinopse no lugar do gênero e prefixo de edição no título.
**Success Criteria**: ao regenerar a 27ª edição, Mundaréu / Manjuba tem 40 livros e BEĨ 56; nenhum livro sem preço de capa tem, na linha do ISBN no PDF, os dois preços; cada id aparece uma vez no catálogo; o relatório mostra, por editora, livros lidos e livros sem preço de capa.
**Tests**: dígito verificador do ISBN; regressões com os PDFs reais de Mundaréu / Manjuba, BEĨ, Olhares e Duna Dueto; ids únicos por editora; links repetidos descartados; gênero sem HTML, preço ou sinopse; título sem "1a ed.".
**Status**: Complete (catálogo da 27ª regenerado: 34.937 livros, 545 preços de feira corrigidos)

## Etapa 7: Ano da edição e catálogo vazio
**Goal**: o site mostra o ano da edição e avisa quando os preços são de uma Festa que já passou; a atualização automática não troca o site para uma edição nova enquanto nenhuma lista dela foi lida.
**Success Criteria**: `edicao.json` traz ano, início e fim; uma edição nova sem listas não escreve catálogo e o site continua na edição anterior.
**Tests**: ano a partir do número da edição; datas a partir do período ("26 e 30 de novembro", "29 de novembro a 3 de dezembro"); build com editoras sem lista não grava nada.
**Status**: Complete

## Etapa 8: Site certo no celular e na tenda
**Goal**: lista legível no celular (preço visível sem arrastar a tabela), preço certo para livros com o mesmo ISBN em duas editoras, link compartilhado malformado sem travar o site, foco do teclado preservado ao adicionar, resumo sem bloco vazio, aviso de quantas editoras já publicaram lista e cache com tempo limite para o sinal fraco da tenda.
**Success Criteria**: em 375 px a lista não tem rolagem lateral; uma lista antiga com ISBN repetido passa para o livro da mesma editora; o site abre com o cache depois de alguns segundos sem resposta da rede.
**Tests**: conferência no navegador (desktop e celular), checagem de sintaxe do script e testes de montagem do site.
**Status**: Complete (conferido no navegador em 375 px e em tela de computador, com rede lenta e sem rede)
