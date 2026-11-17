
        function atualizarNomeArquivo(input, idSpan) {
            const spanNome = document.getElementById(idSpan);
            if (input.files && input.files[0]) {
                spanNome.textContent = input.files[0].name;
                spanNome.style.color = '#b84a62';
                spanNome.style.fontWeight = '600';
            } else {
                spanNome.textContent = 'Nenhum arquivo escolhido';
                spanNome.style.color = '#666';
                spanNome.style.fontWeight = 'normal';
            }
        }
