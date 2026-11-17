
document.addEventListener('DOMContentLoaded', function() {
    const inputCnpj = document.getElementById('cnpj');
    
    if (inputCnpj) {
        inputCnpj.addEventListener('input', function (e) {
            let value = e.target.value.replace(/\D/g, ""); 
            
            if (value.length > 14) {
                value = value.slice(0, 14); 
            }


            value = value.replace(/^(\d{2})(\d)/, "$1.$2");
            value = value.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
            value = value.replace(/\.(\d{3})(\d)/, ".$1/$2");
            value = value.replace(/(\d{4})(\d)/, "$1-$2");

            e.target.value = value;
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
const inputWhatsapp = document.getElementById('whatsapp');
    if (inputWhatsapp) {
        inputWhatsapp.addEventListener('input', function (e) {
            let value = e.target.value.replace(/\D/g, ""); 
            if (value.length > 11) value = value.slice(0, 11);

            value = value.replace(/^(\d{2})(\d)/, "($1) $2");
            value = value.replace(/(\d{5})(\d)/, "$1-$2");

            e.target.value = value;
        });
    }
});