# Defesa do Castelo 🏰

**Jogue agora diretamente no navegador:** [Jogar Defesa do Castelo](https://bepo7.github.io/Trabalho_Final_CG_Beranrdo_Pozzato/)

Bem-vindo ao **Defesa do Castelo**, um jogo desenvolvido em Python (utilizando `py5` e renderização 3D) onde o objetivo é proteger o seu castelo das incansáveis hordas de bonecos de neve malignos!

---

## 🎮 Como Jogar e Regras Básicas

O seu castelo (hasteando a bandeira do Flamengo) possui **3 vidas**. Se um inimigo encostar nos muros do castelo, você perde uma vida!

O campo de batalha é dividido em **5 linhas**. Você controla 5 canhões de neve (um por linha).

### 🎯 Controles de Defesa (A Curva B-Spline)
A principal mecânica do jogo é ajustar o **alcance dos canhões**. Em vez de controlar a força do tiro, você ajusta a altura dos canhões através de **Pontos de Controle** formando uma curva B-Spline.
* **A / D** (ou **← / →**): Seleciona o canhão (linha) que você quer ajustar.
* **W / S** (ou **↑ / ↓**): Sobe ou desce o canhão selecionado. Quanto mais alto o canhão, mais longe a bala alcança na parábola!
* **1 a 5**: Selecionam diretamente uma das 5 linhas.

### ⛄ Inimigos
* **Soldados de Neve:** Inimigos normais que andam em 1 linha.
* **Mini Boss:** Ocupam 2 linhas e possuem muito mais vida.
* **Boss:** Ocupam 3 linhas e são massivos. Aparecem nas ondas finais das fases!

### ⚡ Poderes Especiais
Ao derrotar chefões, você ganha recompensas:
1. **Bolinhas de Poder:** Ao matar um Mini Boss, ele deixa uma bolinha flutuante no chão. Aperte **G** para coletar e ganhar uma carga.
2. **Tiro Rápido:** Aperte **B**, escolha o número do canhão (1 a 5), e aperte **B** de novo. Esse canhão vai atirar feito uma metralhadora por um tempo.
3. **Bomba de Neve:** Ao matar um Boss (ou ter sorte), você ganha esse poder. Aperte **U**, escolha o canhão (1 a 5), e aperte **U** de novo. O próximo tiro causa dano em área, acertando todas as linhas vizinhas!

---
*Trabalho Final de Computação Gráfica.*
*Autor: Bernardo Pozzato.*
