// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertificadosContract {
    address public admin;
    
    struct Certificado {
        uint256 id;
        string nombre;
        string apellidoPaterno;
        string apellidoMaterno;
        string matricula;
        string curso;
        string fechaEmision;
        bool esValido;
    }
    
    mapping(uint256 => Certificado) public certificados;
    
    constructor() {
        admin = msg.sender;
    }
    
    modifier soloAdmin() {
        require(msg.sender == admin, "Solo el administrador puede ejecutar esta funcion");
        _;
    }
    
    function emitirCertificado(
        uint256 _id,
        string memory _nombre,
        string memory _apellidoPaterno,
        string memory _apellidoMaterno,
        string memory _matricula,
        string memory _curso,
        string memory _fechaEmision
    ) public soloAdmin {
        certificados[_id] = Certificado({
            id: _id,
            nombre: _nombre,
            apellidoPaterno: _apellidoPaterno,
            apellidoMaterno: _apellidoMaterno,
            matricula: _matricula,
            curso: _curso,
            fechaEmision: _fechaEmision,
            esValido: true
        });
    }
    
    function obtenerCertificado(uint256 _id) public view returns (
        string memory nombre,
        string memory apellidoPaterno,
        string memory apellidoMaterno,
        string memory matricula,
        string memory curso,
        string memory fechaEmision,
        bool esValido
    ) {
        Certificado memory cert = certificados[_id];
        require(cert.id != 0, "Certificado no existe");
        
        return (
            cert.nombre,
            cert.apellidoPaterno,
            cert.apellidoMaterno,
            cert.matricula,
            cert.curso,
            cert.fechaEmision,
            cert.esValido
        );
    }
    
    function validarCertificado(uint256 _id) public view returns (bool) {
        return certificados[_id].esValido && certificados[_id].id != 0;
    }
    
    function revocarCertificado(uint256 _id) public soloAdmin {
        require(certificados[_id].id != 0, "Certificado no existe");
        certificados[_id].esValido = false;
    }
    
    function transferirAdmin(address nuevoAdmin) public soloAdmin {
        admin = nuevoAdmin;
    }
}
