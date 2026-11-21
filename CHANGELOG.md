# Histórico de mudanças

O que mudou em cada versão do guia. Cada versão tem uma tag no Git e uma release no GitHub com o mesmo texto. As atualizações diárias do catálogo, feitas pelo robô, ficam de fora: elas só trazem listas novas e preços.

## v1.11.0 (21/11/2026)

**Links dos livros que saíam quebrados e letras fora de ordem**

- Quando o endereço do livro é mais largo que a última coluna da tabela, a letra que a borda de fora corta ao meio não caía em célula nenhuma e sumia: "produto/icho-bolota", na Boitatá, no lugar de "produto/bicho-bolota".
- O leitor da tabela põe o sublinhado uns três pontos abaixo das letras em volta. O "_" sumia ("algebra-em-quadrinhos9788521211488", na Blucher, no lugar de "algebra-em-quadrinhos_9788521211488"), ia para o fim do texto, como na Aleph, ou deixava um espaço no meio do endereço, e o link era descartado, como no Sesc SP.
- Letras que a fonte desenha numa peça só, como "tt", "fi" e "rt", trocavam de lugar: "kotetr.com.br", na Kotter, no lugar de "kotter.com.br", e "Norberot Bobbio" e "Filosofai", na Contracorrente, no lugar de "Norberto Bobbio" e "Filosofia".
- No catálogo de 21/11, 1.141 links voltam a abrir a página do livro e 652 livros que estavam sem link ganham o link do PDF, entre eles 509 da Blucher, 291 do Sesc SP, 231 da Aleph, 124 da Martins Fontes e 95 da Ed. UnB. Todos os links da Kotter e da Contracorrente ficam iguais aos do PDF.
- Também voltam certos 22 títulos e 22 autores da Contracorrente, 3 títulos da Nova Fronteira e 16 assuntos da Kotter, da Jujuba, da LVM e da Relicário ("Romance/História Or l" vira "Romance/História Oral"). E o "_x000D_" que a planilha grava no lugar de uma quebra de linha sai dos 20 autores da Ed. UFMG ("Márcia Arbex x000d _ _" vira "Márcia Arbex").

## v1.10.0 (19/11/2026)

**Títulos centralizados da Brasiliense, listas da Com-Arte e da Edusp e listas salvas que acompanham o catálogo**

- A Brasiliense centraliza títulos e autores mais largos que a célula, e a planilha esconde o começo e o fim do texto. O guia mostrava 18 livros com o ISBN e uma letra no lugar do título ("9788511020786 D") e o resto do título no lugar do autor. Agora os 193 livros têm ISBN, esses 18 têm o título e o autor certos, como "A CIDADE DE SAO PAULO GEOGRAFIA E HISTORIA", de Caio da Silva Prado Junior, e outros 23 títulos, 31 autores e 17 assuntos que vinham cortados aparecem inteiros.
- A mesma leitura completa títulos, autores e assuntos cortados em outras listas, como a da Mnema ("ELEGIA GREGA ARCAICA: UMA ANTOLOGIA") e a da Instante ("O ruído de uma época"), e tira 4 cópias quebradas de livros que já estavam no guia.
- A Com-Arte e a Edusp usam o mesmo modelo de planilha, com a quantidade de exemplares antes dos preços e o cabeçalho numa célula só. Na Com-Arte, a quantidade virava o preço de feira de 104 dos 124 livros: "A Casa & Outros Poemas" aparecia por R$ 10,00, e o preço de feira é R$ 18,00. Na Edusp, que trocou a lista em 19/11, a quantidade grudava no autor de 1.055 dos 1.116 livros ("CARLOS, Ana Fani Alessandri25)").
- A lista salva no aparelho passa a pegar do catálogo o título, o autor e o nome da editora, e não só o preço. Um livro salvo com o título quebrado acha o livro certo, e um livro com ISBN de editora renomeada em 18/11 passa a mostrar o nome novo.

## v1.9.0 (18/11/2026)

**Listas da Ed. UFV, da Uneb e da Monolito e código que não muda com o nome da editora**

- A Ed. UFV deixou vazia a coluna do preço com desconto, e a Uneb só publicou o preço de capa. O guia mostrava a capa como preço de feira; agora os 33 livros das duas aparecem com o preço de capa e o aviso de que a editora não informou o preço de feira, como os da Pontes. A Uneb também ganha os autores.
- A Monolito vende a revista com o código de barras do ISSN, e 15 das 52 edições sumiam do guia. As 52 estão lá agora, com o título certo, e a edição 34 deixa de levar o título da 35 colado.
- Em 18/11 o site da Festa trocou o nome de 55 editoras ("Editora Vozes" virou "Vozes"). O código dos livros sem ISBN saía do nome da editora, e 82 deles mudaram de código: na lista salva paravam de atualizar o preço e no link compartilhado sumiam. Agora o código sai do número da editora no site da Festa, que não muda, e o guia acha o livro também pelos códigos antigos.
- O botão que traz a lista de 2025 para 2026 volta a reconhecer as editoras que viraram "Ed." (Unesp, UFMG, Unicamp, UFPR, UFSC, UFV e Unifesp) e a Pontes.

## v1.8.0 (17/11/2026)

**Texto escondido pelas células e preços da Ateliê e da Unesp**

- A lista da Ateliê recorta na borda da célula o texto que não cabe. O leitor devolve à célula o texto inteiro, e a Ateliê passa de 190 para 329 livros, com títulos e autores completos.
- A Ateliê escreve o preço de feira sem os centavos ("60" ao lado de "120.00"), e o site mostrava a capa como preço de feira, o dobro do real.
- Na Unesp, a coluna de quantidade vendida era lida como preço de feira em 649 dos 693 livros: "ABOLICAO" saía por R$ 3,00, e o preço certo é R$ 78,00. Coluna de quantidade nunca vira preço.
- A issue de conferência passa a avisar quando muitos preços de feira ficam abaixo de um quinto da capa.
- No dia, o catálogo da 28ª edição ficou com 18.769 livros de 91 editoras.

## v1.7.0 (16/11/2026)

**Lista da Vozes, letras cortadas e README em português**

- A lista de editoras é lida de novo quando muda no meio da leitura: a Sisko tinha entrado duas vezes e a Seja Breve tinha ficado de fora.
- A lista da Vozes entrou quebrada, com 1.099 linhas sem nenhum ISBN. O leitor que acha menos da metade dos ISBNs do outro deixa de ser escolhido.
- Letra cortada ao meio pela célula (IMS, LavraPalavra, Hucitec e outras), coluna sem bordas (Hucitec), título colado ao autor (Vozes) e ISBN impresso sem o 9 do começo (Ercolano) passam a ser lidos certo.
- O README em português vira a página principal do repositório.
- O selo de visitantes lê o total guardado no repositório e não quebra quando o contador oscila.
- No dia, o catálogo da 28ª edição ficou com 18.576 livros de 89 editoras.

## v1.6.0 (14/11/2026)

**Lista de 2025 levada para 2026 e ISBN sem o último dígito**

- Quem montou a lista com os preços de 2025 leva a lista para 2026 com um botão. Cada livro entra com o preço novo e a etiqueta "Lista de 2025", e os que ainda não estão no catálogo são procurados de novo sempre que o catálogo carrega.
- A Miolo Mole imprime ISBNs sem o último dígito. O leitor recompõe o dígito verificador, e a lista passa de 15 para 36 livros. Foi o primeiro aviso de verdade da issue #17.

## v1.5.0 (13/11/2026)

**Livros recuperados de tabelas quebradas**

- A Letra Selvagem perdia 23 dos 72 livros, porque as bordas da tabela acabam no meio da página, e a Unifesp perdia a última linha. Os livros que só o leitor por posição acha passam a entrar quando os dois leitores leem do mesmo jeito os livros em comum.
- Sai a cópia embaralhada de um livro quando o outro leitor traz o mesmo livro com ISBN.

## v1.4.0 (11/11/2026)

**Preços sem centavos e aviso de lista mal lida**

- As listas da Universo dos Livros (que ficava sem nenhum livro), da Nós (preços escritos como "75" e "37,5") e da Arquipélago (parêntese depois do preço) passam a ser lidas certo.
- Quando uma lista parece mal lida, a atualização diária abre a issue "Listas de preço para conferir" e fecha a issue quando todas as listas voltam a ser lidas.
- A atualização diária passa a ser disparada às 9h55 por uma tarefa agendada no Claude Code, porque o agendamento do GitHub atrasava horas.

## v1.3.0 (09/11/2026)

**Primeiras listas de 2026**

- Lista só com preço de capa, como a da Pontes: os livros aparecem com esse preço e o aviso de que a editora não informou o preço de feira, e o total da lista nunca fica abaixo do real.
- O preço de capa entre traços da Ubu (166 livros) e a planilha impressa em faixas da Phorte (60 livros) passam a ser lidos certo.
- Enquanto só parte das editoras publicou a lista, o catálogo mostra quantas publicaram na edição anterior, para a busca vazia não parecer defeito do guia.
- Cada editora tem o link para a sua lista de preços oficial, o PDF no site da Festa.

## v1.2.0 (18/10/2026)

**Revisão de outubro: preços trocados, livros perdidos e celular**

- 545 livros mostravam o preço de capa como preço de feira (Pallas, Carochinha, Duna Dueto, Vozes e Olhares). Quando falta um dos preços, a linha do ISBN no PDF decide qual é qual.
- Livros que sumiam sem aviso voltam: a Mundaréu / Manjuba aparecia com 2 dos 40 livros e a BEĨ com 9 dos 56.
- O mesmo ISBN em duas editoras ganha um id para cada uma, e a lista deixa de trocar o preço de uma pela outra.
- No celular cada livro vira um cartão, com o preço de feira à direita.
- O topo mostra o ano da Festa e avisa quando os preços são de uma edição que já passou.
- Na tenda, com sinal fraco, o site espera no máximo 3 segundos pela rede antes de usar a cópia guardada.

## v1.1.0 (15/10/2026)

**Prévia do link, contador de visitantes e kit de divulgação**

- O link do site aparece com imagem, título e descrição quando colado no LinkedIn ou no WhatsApp.
- Ícone próprio para quem adiciona o site à tela inicial do iPhone.
- Contador de visitantes únicos, sem cookie e sem nada da lista, com selo nos READMEs.
- Cor principal vermelha no lugar do azul, com contraste conferido nos temas claro e escuro.
- Rodapé mais curto, com a origem dos preços, a privacidade da lista, o contador e o aviso de que o guia não é oficial.
- Kit de divulgação na pasta divulgacao/: post e stories para o Instagram, logo e sugestão de legenda.

## v1.0.0 (02/10/2026)

**Primeira versão do Guia**

- O guia busca no site oficial da Festa a lista de preços de cada editora e lê os PDFs, conferindo cada preço com a linha do ISBN no PDF.
- O catálogo se atualiza sozinho todo dia, de setembro a dezembro, pelo GitHub Actions, e o site é publicado quando o catálogo muda.
- Site no GitHub Pages, sem conta, sem servidor e sem chaves: busca e totais no navegador, lista guardada no próprio aparelho, compartilhamento por link e funcionamento sem internet na tenda.
- Quem importa a lista de outra pessoa vê cada livro com uma etiqueta colorida da lista de origem e pode filtrar por ela.
- O preço de capa da Companhia das Letras (764 livros) e títulos só com números, como 1984, passam a ser lidos certo.
- O nome "Guia não oficial da Festa do Livro da USP", para não parecer site oficial, e a licença PolyForm Noncommercial 1.0.0, com crédito obrigatório.
- No ar com o catálogo da 27ª edição, de 2025, até as editoras publicarem as listas de 2026.
