function atualizarNomeArquivo(input, idSpan) {
            const spanNome = document.getElementById(idSpan);
            if (input.files && input.files.length > 0) {
                if (input.files.length === 1) {
                    spanNome.textContent = input.files[0].name;
                } else {
                    spanNome.textContent = `${input.files.length} arquivos selecionados`;
                }
                spanNome.style.color = '#b84a62';
                spanNome.style.fontWeight = '600';
            } else {
                spanNome.textContent = 'Nenhum arquivo escolhido';
                spanNome.style.color = '#666';
                spanNome.style.fontWeight = 'normal';
            }
        }