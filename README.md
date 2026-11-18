*[Read in English](README.en.md) · Português*

# Guia não oficial da Festa do Livro da USP

**Abra: https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/**

[![Visitantes únicos do guia](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fjvlcapi%2Fguia-nao-oficial-festa-do-livro%2Fmain%2Fdata%2Fselo-de-visitantes.json&label=visitantes%20%C3%BAnicos&color=c0352b&cacheSeconds=3600)](https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/)

Busque nos preços de feira de todas as editoras da [Festa do Livro da USP](https://festadolivro.edusp.com.br) e monte sua lista de compras antes de ir: total na feira, quanto você economiza sobre o preço de capa, gasto por editora e por gênero, orçamento e lista para compartilhar.

Feito por leitores, de graça e de código aberto. **Não é um site oficial da Edusp nem da USP**; os preços vêm das tabelas que as editoras publicam no site oficial e podem mudar até a Festa. Confira no estande.

Quer divulgar? O [kit de divulgação](divulgacao/) tem imagens prontas para o Instagram, a logo e uma sugestão de legenda.

## Para quem vai à Festa

Não precisa de conta, cadastro nem instalar nada. É só abrir o link acima no celular ou no computador.

1. **Busque livros** na aba *Catálogo da feira*: por título, autor, editora ou assunto. Dá para filtrar por editora (estande) e por faixa de preço, e ordenar por menor preço ou maior desconto. Ao escolher uma editora aparece o link para a lista de preços oficial dela (o PDF no site da Festa); o mesmo link fica no topo de cada editora em *Minha lista*.
2. **Toque em Adicionar** nos livros que você quer.
3. **Veja a conta** na aba *Minha lista*: total na feira, economia sobre o preço de capa, gasto por editora e por gênero. Se quiser, defina um orçamento e acompanhe quanto ainda sobra.
4. **Leve para a feira.** Abra o site uma vez com internet: depois disso ele funciona mesmo sem sinal, dentro da tenda. No celular, use *Adicionar à tela inicial* para abrir como um aplicativo.

### Onde fica a minha lista

A lista fica salva **só no navegador do seu aparelho**. Nada da lista é enviado para servidor nenhum e ninguém mais vê. A única coisa que o site manda para fora é um +1, uma vez por navegador, para o contador público de visitantes que aparece no topo desta página, sem cookies. Se você limpar os dados do navegador ou usar janela anônima, a lista se perde.

### Compartilhar a lista

Em *Minha lista*, toque em **Compartilhar lista**, escreva seu nome (opcional) e toque em **Copiar link** ou **Enviar…**. Mande o link para quem quiser, por exemplo no WhatsApp.

Quem abrir o link vê a sua lista com o total e os preços atuais, e pode tocar em **Adicionar estes livros à minha lista** para copiar os livros para a própria lista. O mesmo link serve para **passar a lista do celular para o computador** (ou o contrário).

Os livros que vieram de uma lista compartilhada ganham uma **etiqueta colorida com o nome da lista** (por exemplo, "Lista de Ana"), com uma cor para cada lista importada. Acima dos livros, os filtros *Todos*, *Adicionados por mim* e uma etiqueta por lista mostram só os livros de cada origem, o que ajuda quando a lista fica grande.

O link leva só os livros escolhidos e o nome que você digitou; ele não dá acesso a mais nada do seu aparelho.

### Quando sai a edição de um ano novo

Enquanto as listas da nova Festa não saem, o topo do site avisa de qual edição são os preços mostrados. Quando saem, o site passa a mostrar o catálogo da nova edição e a sua lista recomeça vazia. As listas de anos anteriores continuam guardadas no aparelho e aparecem num seletor de edição, só para consulta.

Para levar a lista do ano passado para o ano novo, abra a lista antiga no seletor de edição e toque em **Trazer os livros para a lista** do ano novo. O mesmo botão aparece na lista nova enquanto ela está vazia. Cada livro é procurado no catálogo novo pelo ISBN, ou pelo título na mesma editora, e entra com o preço deste ano e a etiqueta "Lista de 2025". Os que não estão ficam num aviso no alto da lista, separados entre os de editoras que ainda não publicaram a lista do ano e os que a editora não trouxe. Toda vez que o catálogo atualiza, o guia procura esses livros de novo e traz os que chegarem. A lista antiga continua igual.

---

## Para quem mantém o projeto

### Como funciona

```
site oficial da Festa (API pública + PDFs de preço das editoras)
        │  python -m festa_do_livro build        (GitHub Actions, ou local)
        ▼
data/<edição>/catalogo.json   livros, preços e editoras
data/<edição>/edicao.json     nome e datas da edição
data/<edição>/relatorio.md    conferência dos preços contra os PDFs
        │  python -m festa_do_livro assemble-site → _site/
        ▼
GitHub Pages: site/index.html + catalogo.json + edicao.json
        │
        ▼
navegador de cada pessoa: busca, lista e totais (lista salva no próprio aparelho)
```

- **Edição**: `settings.json` tem `"edition": "auto"`, que usa a edição declarada na página inicial do site oficial. Para fixar uma edição, troque por exemplo para `"28-festa-do-livro-da-usp"` ou passe a variável `FESTA_EDITION`. Uma edição nova sem nenhuma lista lida não troca o site: o `build` nunca grava catálogo vazio. O ano vem do número da edição (a Festa é anual desde 1999) e as datas, do texto do site oficial.
- **Editoras**: a lista de editoras vem da API do site oficial, 40 por página. Quando uma editora se inscreve enquanto as páginas são lidas, as outras andam uma posição: uma aparece duas vezes e outra fica de fora (aconteceu em 16/11/2026). Por isso as páginas são lidas de novo até baterem com o total que o site informa.
- **Leitura dos PDFs**: cada lista é lida de dois jeitos (células da tabela e posição do texto) e fica o resultado mais completo. O leitor que acha menos da metade dos ISBNs do outro perde, mesmo lendo mais linhas: na Vozes de 2026, as bordas da tabela só separam algumas colunas, e o leitor de tabela leu 1.099 linhas sem nenhum ISBN, contra 1.092 livros com ISBN do outro leitor. Os livros que só o outro leitor achou entram também, desde que os dois leiam do mesmo jeito os livros em comum: assim voltam as linhas de uma tabela que perde as bordas no meio da página, sem deixar entrar lixo de um leitor que trocou as colunas. Se o leitor escolhido tinha lido uma dessas linhas sem o ISBN, ou com o ISBN colado no título, essa cópia sai, para o livro não aparecer duas vezes. Texto que a célula corta na borda é lido inteiro: a planilha esconde o resto atrás do recorte da célula, mas o PDF guarda o texto todo (na Ateliê de 2026, "A Cidade e os Ca" é "A Cidade e os Cachorros: Biografia de um Romance", e o ISBN "978-85-7480-442" é o 978-85-7480-442-2). Conta como cortado só o texto que aparece do começo até a borda e some dali em diante; texto desenhado sobre várias células fica como estava. Como o leitor por posição ainda vê o título cortado, título cortado e título inteiro que começa igual contam como a mesma leitura na hora de comparar os dois leitores. Nomes que continuam cortados são completados pelo texto do PDF. Na coluna dos ISBNs, um código sem palavras que não é ISBN (ISSN de revista, ISBN digitado com erro) não vira título, e código de barras longo conta como número da coluna: na Monolito de 2026, 15 das 52 edições da revista vêm com o código do ISSN ("977217974800703") e sumiam do catálogo, e o ISBN seguido do número da edição ("978856627513110") vale como o ISBN. No cabeçalho, "autor" vale antes de "nome": "Nome dos autor(es)", na Uneb de 2026, é a coluna do autor. Texto que só cita um site no meio de outras palavras ("Shutterstock.com, Freepik.com" no fim dos autores, na Ciranda Cultural) não é link. Quando um leitor acha só um preço, a linha do mesmo ISBN no PDF decide qual é o de capa e qual é o de feira. Coluna de preço de feira que larga os centavos ("60" e "41,5" ao lado de "120.00" e "83.00", na Ateliê de 2026) também é preço, desde que fique abaixo da capa e acima de um quinto dela na maioria das linhas e tenha centavos em algumas; quantidade e número de páginas não passam nisso. Coluna cujo cabeçalho conta exemplares ("Qtd. Vend", na Unesp de 2026) nunca é preço: lida como preço, a quantidade vendida virava o preço de feira ("ABOLICAO" por R$ 3,00, e não R$ 78,00). O ISBN só vale com o dígito verificador certo, o que pega número de planilha em notação científica e ISBN quebrado em duas linhas; livros diferentes com o mesmo ISBN continuam separados. ISBN impresso sem o último dígito, mas com o hífen antes dele ("978-65-81555-00-"), ganha o dígito de volta, porque o dígito verificador sai dos outros doze; sem isso o leitor tomava o número por texto, empurrava título, autor e editora uma coluna para o lado e o livro sumia do catálogo. Quando uma célula estreita corta o texto no meio de uma letra, o meio dessa letra cai na célula seguinte; a letra volta para o texto que ela termina, em vez de abrir o autor ("SSonia Salzstein", no IMS de 2026) ou o link. Só voltam letras (um dígito mudaria um preço) que terminam uma linha contínua da célula da esquerda e que não começam um texto que transborda da própria célula. Uma coluna que perde as bordas entre as linhas vira uma célula alta com os valores de várias linhas (na Hucitec de 2026, 31 preços de capa numa célula só), e cada valor volta para a linha em que está impresso. No leitor por posição, título longo e autor grudados no mesmo trecho de texto ("...LOGOTERAPIA DE VIKTOAna Clara...", na Vozes de 2026) são separados onde uma letra começa exatamente no ponto em que a coluna do autor começa o texto, desde que a maioria dos textos da coluna do título termine antes dali. ISBN impresso sem o 9 do começo ("786585960589", na Ercolano de 2026) também abre uma linha, para o livro não grudar no de baixo; ele entra sem ISBN. Planilha impressa em faixas (primeiro ISBN e título, depois autor e preço) é colada de volta linha a linha; no relatório ela aparece como "tabela em faixas" e com divergências, porque ISBN e preço ficam em páginas diferentes. Assunto que é uma lista de etiquetas ("Alfabetização, Inglês, Primeiros conceitos", na Ciranda Cultural) fica, cortado na última etiqueta inteira que cabe em 60 letras; sinopse no lugar do assunto sai. Livro de lista só com preço de capa aparece com esse preço e o aviso de que a editora não informou o preço de feira; no total da lista ele entra pelo preço de capa, para o orçamento nunca ficar abaixo do real. A lista é só de capa quando o cabeçalho tem um único rótulo de preço e ele diz "capa" (valor em reais antes do primeiro ISBN não conta como rótulo: na Uneb de 2026 o ISBN vem depois do preço), ou quando a coluna de preço de feira está vazia em quase toda linha com ISBN (na Ed. UFV de 2026, "Preço com Desconto" não tem nenhum valor).
- **Conferência**: cada preço de capa e de feira precisa aparecer na linha do mesmo ISBN no PDF. O que não bate vai para o relatório, que também mostra, por editora, livros lidos e livros sem preço de capa.
- **Site**: estático, sem servidor nem conta. A lista fica no `localStorage`, separada por edição, e os preços dela são atualizados quando o catálogo muda. O link de compartilhamento leva a edição, o nome e os identificadores dos livros no fragmento da URL (`#lista=...`), que o navegador não envia ao servidor. O `site/sw.js` guarda o site e o catálogo no aparelho para funcionar sem internet: vai primeiro na rede, mas depois de 3 segundos sem resposta usa a cópia guardada, porque na tenda o celular mostra sinal e não passa dados. O mesmo ISBN vendido em duas editoras tem um id para cada uma (o ISBN e um sufixo), e listas antigas são ajustadas sozinhas quando o catálogo muda. O sufixo e o id de livro sem ISBN saem do número da editora no site da Festa (o "publisher-474" do endereço da lista), e não do nome: em 18/11/2026 a Festa trocou o nome de 55 editoras, e 82 livros sem ISBN mudaram de id. Cada livro leva no catálogo os ids que teve com cada nome da editora (campo `o`, feito a partir de `data/<edição>/nomes-usados-nos-codigos-antigos.json`, que guarda todo nome que cada editora teve na edição), e a lista salva ou o link compartilhado com um id antigo acha o livro e passa para o id novo. A lista de uma edição anterior é trazida para a atual livro a livro: pelo ISBN, preferindo a mesma editora, ou pelo mesmo título na mesma editora. A editora é comparada sem maiúsculas, acentos e palavras como "Editora", "Ed.", "Editores" e "Edições", porque em 2026 14 das 60 editoras escreveram o nome de outro jeito ("Aller" virou "Aller Editora") e em 18/11 a Festa trocou "Editora Unesp" por "Ed. Unesp" e "Pontes Editores" por "Pontes". Os livros que faltam ficam em `listasTrazidas`, na lista da edição atual, e são procurados de novo a cada carga do catálogo.
- **Contador de visitantes**: na primeira vez que um navegador abre o site publicado (`jvlcapi.github.io`), a página chama `abacus.jasoncameron.dev/hit/...` e anota no `localStorage` que já contou. Cópias locais e forks não contam. O selo do topo mostra o total que o robô guarda no repositório uma vez por dia, porque o serviço do contador às vezes sai do ar: em novembro de 2026, o selo que lia o contador direto passou dias mostrando "inaccessible". Não é exato (quem limpa o navegador conta de novo, e quem só usa o site sem internet não conta), mas dá a dimensão do alcance.

### Atualização automática (GitHub Actions)

- **Atualizar catálogo** (`atualizar-catalogo.yml`): roda todo dia de setembro a dezembro e pelo botão *Run workflow* (com a edição opcional). Roda os testes, gera catálogo e relatório, mostra o relatório no resumo da execução e, se algo mudou, faz commit e publica o site. Quando uma lista parece mal lida (nenhum livro, a maioria sem preço de capa, linhas perdidas, muitos preços que não aparecem no PDF ou muitos preços de feira abaixo de um quinto da capa), o job `avisar` abre a issue "Listas de preço para conferir", que chega por e-mail. Um problema já avisado não é avisado de novo, e a issue fecha sozinha quando todas as listas voltam a ser lidas sem problema.
- **Hora certa**: o agendamento do GitHub (marcado para 6h de Brasília) atrasa horas; em 2026 rodou entre 9h30 e 16h15. Por isso uma tarefa agendada na nuvem do Claude Code, na conta do mantenedor, dispara o *Atualizar catálogo* pela API do GitHub às 9h55, e o site fica atualizado por volta das 10h. O agendamento do GitHub continua de reserva: quando roda depois, só publica se alguma lista mudou. Se o GitHub tiver desligado a rotina (ele faz isso com agendamentos de repositório público depois de 60 dias sem atividade), a tarefa religa antes de disparar.
- **Publicar site** (`publicar-site.yml`): monta `_site/` com a edição atual (`data/edicao-atual.json`) e publica no GitHub Pages. Também roda quando `site/` ou os dados mudam por push.
- **Testes** (`testes.yml`): em todo push e pull request.
- **Guardar contador de visitantes** (`guardar-contador-de-visitantes.yml`): todo dia às 7h de Brasília, lê o total com `/get/...`, sem somar, e grava em `data/selo-de-visitantes.json`, o arquivo que o selo do topo lê, e em `data/visitantes.csv` quando ele mudou. Assim o selo funciona com o contador fora do ar, o histórico fica no repositório mesmo que o serviço suma, e a leitura diária impede que o contador expire (o serviço apaga contadores sem acesso por 6 meses). Se o contador não der o total, a rodada só deixa um aviso, e o selo fica com o último total guardado.

### Roteiro do dia em que a lista sair

1. Confirme a edição: `python -m festa_do_livro detect-edition` (ou veja a página de editoras no site oficial).
2. Rode o workflow **Atualizar catálogo** (vazio = `auto`, ou informe a edição).
3. Abra o resumo da execução e leia o relatório: total de livros, listas não lidas e divergências por editora. Editora com formato novo aparece com 0 livros, com muitas divergências, com muitos livros sem preço de capa ou com "Lidos" bem acima de "Livros".
4. Se precisar ajustar o leitor, corrija, adicione um teste com o PDF da editora em `tests/fixtures/price_lists/` e rode de novo.
5. Abra o site e confira que o número e as datas da nova edição aparecem no topo.

### Versões

Cada atualização do código vira uma versão, como `v1.8.0`, com tag no Git, release no GitHub e uma seção no [CHANGELOG.md](CHANGELOG.md) dizendo o que mudou. A tag aponta para o último commit que foi ao ar naquele dia. As atualizações diárias do catálogo, feitas pelo robô, não mudam a versão.

### Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
.venv/bin/python -m festa_do_livro detect-edition
.venv/bin/python -m festa_do_livro build
.venv/bin/python -m festa_do_livro assemble-site
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

O `build` baixa os PDFs para `cache/<edição>/` (fora do Git) e escreve em `data/`. Para outra edição: `--edition 28-festa-do-livro-da-usp`. Depois do último comando, o site fica em http://127.0.0.1:8765.

### Segredos

Nenhuma chave é necessária: o site oficial e a API são públicos, o commit automático usa o `GITHUB_TOKEN` que o GitHub gera em cada execução e a publicação no Pages usa o token temporário do próprio GitHub (OIDC). O repositório tem *secret scanning* e *push protection* ligados. Se um dia for preciso uma chave (por exemplo, para notificações):

1. Cadastre em *Settings → Secrets and variables → Actions*.
2. Passe para o passo do workflow como `env: NOME: ${{ secrets.NOME }}` e leia com `os.environ` no código.
3. Para uso local, coloque num `.env` (já ignorado pelo Git), nunca em `settings.json`.

O teste `tests/test_repository_hygiene.py` falha se algum arquivo versionado tiver padrão de token ou chave, e confere que `.env` e `cache/` estão ignorados. O catálogo também descarta links com parâmetros de credencial que vêm em algumas listas de editoras.

### Estrutura

```
CHANGELOG.md                  o que mudou em cada versão (cada uma tem tag e release no GitHub)
settings.json                 edição ("auto" ou identificador) e endereço do site oficial
src/festa_do_livro/
  fair_site.py                página inicial, API do evento e das editoras
  price_list_download.py      download dos PDFs com cache
  pdf_reading.py              extração de tabelas, texto e posições
  table_parser.py             leitor por células da tabela
  position_parser.py          leitor por posição do texto
  catalog_builder.py          limpeza, nomes completos, links seguros, catalogo.json
  price_verification.py       conferência de preços e relatório
  site_assembly.py            monta a pasta publicada no GitHub Pages
site/                         site público (página, cache offline, ícone, manifesto)
divulgacao/                   kit de divulgação: imagens para Instagram, logo e legenda
data/                         catálogos gerados (um diretório por edição) e o total diário de visitantes (visitantes.csv com o histórico, selo-de-visitantes.json com o número do selo)
```

## Licença

Código, site e documentação: [PolyForm Noncommercial 1.0.0](LICENSE.md). Você pode usar, estudar, modificar e compartilhar para fins não comerciais, desde que toda cópia mantenha os termos da licença e a linha de crédito:

```
Required Notice: Copyright 2026 João Vitor Lopes Capi (https://github.com/jvlcapi)
```

Uso comercial só com autorização por escrito do autor.

Os dados dos livros (títulos, autores e preços) vêm das listas que as editoras publicam no site oficial da Festa e não estão cobertos por esta licença. Os PDFs em `tests/fixtures/price_lists/` são essas listas públicas, guardadas só para testar o leitor.
