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

## Etapa 9: Formatos novos das listas da 28ª edição
**Goal**: ler direito as listas que chegaram em novembro de 2026 em formatos que o leitor ainda não conhecia: preço de capa seguido de parêntese ("69,90)", Arquipélago), preços sem centavos ("75" e "37,5", Nós), preço de três dígitos alinhado à direita que escapava para o título e planilha impressa em duas faixas da mesma largura (ISBN e título, depois capa e preço USP, Universo dos Livros). A conferência de preços passa a aceitar o preço de feira calculado a partir da porcentagem de desconto (Instituto Tomie Ohtake).
**Success Criteria**: Arquipélago com preço de capa nos 63 livros; Nós com os 143 livros, sem preço no lugar do autor; Universo dos Livros com 358 livros em vez de nenhum; Tomie Ohtake sem divergências; nas outras listas (191 da 27ª e 44 da 28ª) nenhum livro some e nenhum preço que já era lido muda.
**Tests**: regressões com os PDFs reais da Nós e da Universo dos Livros; preço com parêntese; faixas da mesma largura; linha com ISBN e preço juntos nunca colada como faixa; preço de feira que segue ou não a porcentagem.
**Status**: Complete (comparação com os 238 PDFs: só essas listas e quatro da 27ª mudaram, todas ganhando o preço de capa que o PDF traz)

## Etapa 10: Aviso de lista com erro
**Goal**: a atualização diária avisa quando uma lista parece mal lida, em vez de publicar em silêncio. O build grava `listas-para-conferir.json` e põe as listas no topo do relatório; o job `avisar` abre, comenta ou fecha a issue "Listas de preço para conferir", que chega por e-mail.
**Success Criteria**: aplicadas às listas da 28ª lidas pelo leitor antigo, as regras apontam exatamente as quatro que estavam erradas (Universo dos Livros, Nós, Arquipélago e Tomie Ohtake) e, com o leitor novo, nenhuma; o mesmo problema nunca é avisado duas vezes; a issue fecha sozinha quando tudo volta a ser lido; a falha do aviso não segura a publicação.
**Tests**: cada regra (nenhum livro, linhas perdidas, sem preço de capa, preços fora do PDF, lista não baixada) e o que não deve avisar (lista boa, lista em faixas, editora sem lista ainda); abrir, comentar só o novo, fechar, respeitar a issue fechada e reabrir para problema novo; busca da issue pelo título exato; comando que entrega as listas à issue.
**Status**: Complete

## Etapa 11: Livros perdidos em tabelas quebradas
**Goal**: trazer de volta os livros que somem quando a tabela do PDF quebra. Na Letra Selvagem as bordas acabam no meio da página e 23 dos 72 livros sumiam; na Unifesp a última linha tem a célula partida. O leitor por posição passa a ler coluna de preços quase toda sem centavos ("80" e "40" ao lado de "44,9"), preço escrito à esquerda da célula e ISBN digitado com um dígito a menos. Os livros que só o outro leitor achou entram quando os dois leem do mesmo jeito os livros em comum, e a cópia que o leitor escolhido tinha lido embaralhada (sem ISBN ou com o ISBN colado no título, como "Prisma da raça" na Unifesp) sai, para o livro não aparecer duas vezes.
**Success Criteria**: Letra Selvagem com 72 livros e Unifesp com "Prisma da raça" uma vez só, com ISBN, autor e preço certos; a 28ª remontada só difere do catálogo publicado antes da cópia sair por essa cópia, e nas listas guardadas só saem cópias embaralhadas (35 em duas listas da 27ª), nunca outro volume da mesma série com o mesmo preço; comparando, ISBN a ISBN, cada PDF da 28ª com o catálogo, só ficam de fora livros com preço R$ 0,00 (126 da Pontes e 2 da Unifesp); nas 310 listas guardadas (27ª e 28ª) nenhum livro some nem muda de preço, e os 502 livros novos têm o preço da linha do seu ISBN.
**Tests**: regressões com os PDFs reais da Letra Selvagem e da Unifesp (linhas abaixo das bordas, lista inteira, preço à esquerda da célula, última linha com a célula partida); outro leitor aproveitado quando concorda nos livros em comum e ignorado quando lê de outro jeito; "Prisma da raça" uma vez só no PDF real da Unifesp; cópia embaralhada que sai (ISBN no título, mesmo título sem ISBN) e livros que ficam (outro volume com o mesmo preço, mesmo título com outro preço).
**Status**: Complete

## Etapa 12: Trazer a lista de uma edição anterior
**Goal**: quem montou a lista com os preços de 2025 leva essa lista para 2026 com um botão, na lista da edição anterior (e na lista vazia da edição atual). Cada livro é procurado no catálogo deste ano pelo ISBN, preferindo a mesma editora, ou pelo mesmo título na mesma editora, e entra com o preço novo e a etiqueta "Lista de 2025". Os que não estão ficam num aviso na lista, separados entre editoras que ainda não publicaram a lista deste ano e livros que a editora não trouxe; quando o catálogo atualiza, o guia procura esses livros de novo e traz os que chegarem. A editora é comparada sem maiúsculas, acentos e palavras como "Editora", porque 14 das 60 editoras de 2026 escreveram o nome de outro jeito ("Aller" virou "Aller Editora").
**Success Criteria**: numa lista de 2025 com livros de todos os casos (mesmo ISBN com preço novo, livro sem ISBN e livro com ISBN novo achados pelo título, livro sem ISBN de editora que mudou o nome, editora sem lista de 2026, editora que publicou sem o livro, inclusive com o nome mudado, livro que já estava na lista de 2026), cada um vai para o lugar certo; a lista de 2025 continua igual; um livro que chega depois entra sozinho e sai do aviso; "Esquecer esses livros" apaga o aviso; nada quebra em 375 px.
**Tests**: conferência no navegador com uma lista de 2025 montada com livros reais dos dois catálogos (desktop e 375 px), checagem de sintaxe do script e testes de montagem do site.
**Status**: Complete (conferido no navegador em 375 px e 1100 px com 12 livros reais de 2025: 6 achados, um deles já na lista de 2026, 3 esperando a editora publicar e 3 que a editora não trouxe)

## Etapa 13: ISBN impresso sem o último dígito
**Goal**: ler as listas que imprimem o ISBN sem o último dígito, mas com o hífen antes dele ("978-65-81555-00-", Miolo Mole, primeiro aviso de verdade da issue "Listas de preço para conferir", em 14/11/2026). O leitor de tabelas tomava o número por texto, empurrava título, autor e editora uma coluna para o lado, e o catálogo descartava a linha porque o "título" era só número: 21 dos 36 livros sumiam. O dígito que falta é o verificador, que sai dos outros doze, então o ISBN volta inteiro, e a conferência de preços acha a linha desse ISBN no PDF.
**Success Criteria**: Miolo Mole com os 36 livros, "Garoto Avatar" com ISBN 9786581555009, autor e preços certos, e nenhuma divergência de preço; 14 dos 21 ISBNs recompostos batem com os mesmos livros na lista da editora em 2025; ISBN com um dígito faltando no meio ("978-658984119", Letra Selvagem) continua sem ISBN; nas outras listas guardadas (27ª e 28ª) nenhum livro muda.
**Tests**: dígito recomposto e números que não ganham dígito (sem hífen no fim, dois dígitos a menos, sem 978 ou 979, ISBN inteiro, texto depois do hífen); colunas no lugar na linha com o ISBN cortado; regressão com o PDF real da Miolo Mole (livro lido, lista inteira, preços conferidos); conferência que acha o ISBN cortado e para no ISBN cortado seguinte.
**Status**: Complete (nas 282 listas guardadas, só a Miolo Mole mudou, de 15 para 36 livros, sem divergência de preço; o build completo da 28ª fica com 13.920 livros e nenhuma lista para conferir)

## Etapa 14: Leitor que perde os ISBNs não é escolhido
**Goal**: ler a lista da Vozes de 2026, que entrou quebrada em 16/11/2026: 644 "livros" com o nome do autor no lugar do título, sem ISBN e sem preço de capa. As bordas da tabela só separam algumas colunas, e o leitor de tabelas junta os ISBNs, títulos e preços de capa de uma página inteira numa célula só: lê 1.099 linhas sem nenhum ISBN. O leitor por posição lê 1.092 livros, todos com ISBN válido, mas perdia porque a escolha só contava título e preço de feira. Agora o leitor que acha menos da metade dos ISBNs válidos do outro perde, mesmo lendo mais linhas.
**Success Criteria**: Vozes com cerca de 1.090 livros, com ISBN, título, autor e os dois preços, sem divergência de preço; nas 282 listas guardadas (27ª e 28ª), só a Vozes e a Ercolano (ISBN e autor colados no título) trocam de leitor, e nas outras nenhum livro muda.
**Tests**: escolha entre os dois leitores (o que perdeu os ISBNs perde, de cada lado; com ISBNs dos dois lados vale a contagem de livros completos; poucos ISBNs não decidem); regressão com as primeiras páginas do PDF real da Vozes (livro lido com ISBN, autor e preços; todos os ISBNs dessas páginas; preços conferidos) e com o PDF real da Ercolano.
**Status**: Complete (nas 282 listas guardadas, só a Vozes e a Ercolano trocaram de leitor: a Vozes foi de 1.099 linhas sem ISBN para 1.092 livros com ISBN, 1.089 com preço de capa, e a Ercolano de 34 títulos com ISBN e autor colados para 32 livros com ISBN; o build completo da 28ª fica com 18.340 livros, nenhuma divergência nova e nenhuma lista para conferir. Ficam defeitos do próprio PDF: na Vozes, 98 livros sem autor, a maioria com o autor cortado no fim do título longo; na Ercolano, o ISBN de "A guerra das bichas" está impresso errado e o livro gruda em "A revolta dos bichos")

## Etapa 15: Lista de editoras que muda no meio da leitura
**Goal**: o site oficial mostra as editoras de 40 em 40. Quando uma editora se inscreve enquanto as páginas são lidas, as outras andam uma posição: uma aparece duas vezes e outra fica de fora (16/11/2026: a Sisko entrou duas vezes e a Seja Breve ficou de fora). O guia lê as páginas de novo até uma leitura bater com o total que o site informa, sem editora repetida.
**Success Criteria**: editora inscrita no meio da leitura entra, e nenhuma aparece duas vezes; sem mudança, as páginas são lidas uma vez só; se a lista não parar de mudar, o guia segue com as editoras da última leitura, sem repetição.
**Tests**: leitura de novo quando o total muda entre as páginas; páginas lidas uma vez quando nada muda; lista que não para de mudar sem editora repetida.
**Status**: Complete (no site oficial de 16/11, as 87 editoras vieram numa leitura só, em 3 páginas, sem repetição)

## Etapa 16: Letra cortada ao meio volta para o texto dela
**Goal**: em listas com células estreitas, o PDF corta o texto no meio de uma letra, e o meio dessa letra cai na célula seguinte. O leitor de tabela põe cada letra na célula onde fica o meio dela, então o autor começava com a última letra do título ("SSonia Salzstein" no IMS de 2026, "RGirondo, Oliverio" na 34) e os links ganhavam uma letra antes do endereço ("https://Nhttps://editora34.com.br/..."). Agora a letra volta para o texto que ela termina quando é letra (um dígito mudaria um preço: na Unesp, "23,00" virava "3,00"), quando termina uma linha contínua da célula da esquerda e quando não começa um texto que transborda da própria célula: depois dela vem texto por cima, um espaço, ou a letra seguinte começa onde a coluna costuma começar o texto. Assim o "Q" de "QUADRINHOS NA CIA" (Companhia das Letras e JBC, 2025), que transborda para a esquerda, fica onde está.
**Success Criteria**: na 28ª, autores que começam com letra solta caem de 553 para 79 e links colados de 538 para 8; IMS e LavraPalavra sem nenhum autor com letra solta; nenhum livro sai, nenhum preço muda e nenhuma divergência nova aparece nas 282 listas guardadas.
**Tests**: letra cortada volta para o texto que termina; primeira letra que começa pouco antes da borda fica na sua célula; texto que transborda para a esquerda fica inteiro; dígito cortado fica onde está o meio dele; regressão com a primeira página real do IMS e da LavraPalavra.
**Status**: Complete (nas 282 listas guardadas, 1.362 autores perdem a letra solta, 1.220 títulos ganham a letra que faltava e 585 links ficam limpos, sem livro perdido nem preço trocado)

## Etapa 17: Coluna que perde as bordas entre as linhas
**Goal**: na página 8 da lista da Hucitec de 2026, a coluna do preço de capa perde as bordas entre as linhas. O PyMuPDF lê uma célula alta com 31 preços na primeira linha e nada nas de baixo, e o leitor, vendo essa coluna quase sempre vazia, deixava de lê-la como preço: 39 livros ficavam sem preço de capa. Agora a célula mais alta que as outras da sua linha é dividida, e cada linha de texto volta para a linha da tabela em que está impressa, desde que as linhas cobertas tenham células próprias. Na L&PM de 2025, todas as células de um livro atravessam as duas linhas do link, e nada se divide.
**Success Criteria**: Hucitec com preço de capa em todos os livros, sem divergência ("Estrela e o sensitivo" com R$ 77,00 e R$ 38,50); a Vozes de 2025 ganha o ISBN de cada livro da primeira página e a Olhares de 2025 ganha três preços de capa; nenhuma lista perde livro.
**Tests**: cada linha da célula alta vai para a linha em que está impressa; livro cujas células atravessam as duas linhas do link fica inteiro; célula que ocupa várias colunas fica inteira; regressão com a página 8 real da Hucitec (preço lido, todos com capa, preços conferidos).
**Status**: Complete (Hucitec com 0 livros sem capa, contra 39; na 28ª, livros sem capa caem de 44 para 5)

## Etapa 18: Título e autor no mesmo trecho de texto
**Goal**: na Vozes de 2026, o título longo é cortado na largura da coluna, e o PyMuPDF junta o que sobra dele e o autor num trecho só ("A AUTOTRANSCENDENCIA NA LOGOTERAPIA DE VIKTOAna Clara de Andrade Patricio"): 98 livros ficavam sem autor, com o nome no fim do título. O leitor por posição passa a guardar onde começa cada letra e corta o trecho onde uma letra começa exatamente no ponto em que uma coluna de palavras alinhada à esquerda começa o texto. Esse ponto só vale quando textos diferentes começam nele, ou quando a coluna inteira repete o mesmo nome ("VOZES"), porque preços alinhados à direita e assuntos centralizados também repetem um ponto de início: na Vozes de 2025, "23,55" virava "23," e "55"; na Todavia de 2025, "FICÇÃO BRASILEIRA" virava "FICÇÃO B" e "RASILEIRA". Número nunca é cortado.
**Success Criteria**: Vozes de 2026 com 33 livros sem autor, contra 98 (os que sobram não trazem autor nem na coluna do autor nem colado ao título); Estação Liberdade com o autor na coluna de autor e a editora na de editora; nenhum assunto centralizado cortado.
**Tests**: corte onde a coluna do autor começa; o pedaço do autor começa no ponto da coluna; texto que passa do ponto sem letra ali fica inteiro; coluna alinhada à direita não tem ponto exato; assunto centralizado repetido não é ponto de coluna; nome que a coluna inteira repete é; regressão com as três primeiras páginas da Vozes de 2026 (autor separado do título longo e do título cortado no meio da palavra; só os livros sem autor no PDF ficam sem autor).
**Status**: Complete (nas 282 listas guardadas, 431 autores saem de dentro do título; na 28ª, livros sem autor caem de 1.743 para 1.658)

## Etapa 19: ISBN impresso sem o 9 do começo
**Goal**: na Ercolano de 2026, o ISBN de "A guerra das bichas" está impresso como "786585960589". O leitor por posição não via ali o começo de uma linha e juntava o livro ao de baixo: "A revolta dos bichos" aparecia com o título dos dois e o preço de "A guerra das bichas" (R$ 89,90 em vez de R$ 57,50), e a conferência não acusava porque a janela dela começa antes do ISBN. Agora um número de doze dígitos que começa com 78 ou 79 também abre uma linha, e o livro entra sem ISBN, porque o número não fecha com o dígito verificador. Na mesma lista, o link largo demais para a célula centralizada perdia o começo para o assunto ("Ensaio ps://ercolano.com.br/..."), e esse pedaço de link sai do assunto.
**Success Criteria**: Ercolano com 33 livros, contra 32; "A guerra das bichas" sem ISBN, de Copi, com R$ 89,90 e R$ 44,95; "A revolta dos bichos" com o ISBN dela, de Mykola Kostomárov, com R$ 57,50 e R$ 28,75; "Complementos à teoria sexual sobre o" com assunto "Ensaio" e autor "Pascal Quignard".
**Tests**: ISBN sem o 9 do começo abre linha; regressão com o PDF real da Ercolano (os dois livros separados, autor separado do título cortado, pedaço de link fora do assunto).
**Status**: Complete (Ercolano com 33 livros, todos com autor, e nenhuma divergência)

