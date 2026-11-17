document.addEventListener("DOMContentLoaded", function() {
    const inputCep = document.getElementById('cep');

    if (inputCep) {
        inputCep.addEventListener('blur', function() {
            let cep = this.value.replace(/\D/g, ''); // Remove traços, pontos ou espaços

            if (cep.length === 8) {
                fetch(`https://viacep.com.br/ws/${cep}/json/`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.erro) {
                            preencherCampo('rua', data.logradouro);
                            preencherCampo('bairro', data.bairro);
                            preencherCampo('cidade', data.localidade);
                            preencherCampo('estado', data.uf);

                            let inputNumero = document.getElementById('numero');
                            if (inputNumero) inputNumero.focus();
                        } else {
                            alert('CEP não encontrado na base do ViaCEP.');
                        }
                    })
                    .catch(error => console.error('Erro ao buscar CEP:', error));
            }
        });
    }
});

function preencherCampo(id, valor) {
    let campo = document.getElementById(id);
    if (campo) {
        campo.value = valor;
    }
}