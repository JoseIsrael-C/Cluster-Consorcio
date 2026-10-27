// Synthetic but realistic records for the earlier prototype (D1), built the way its Django views call
// emitirCertificado (management/views.py of the prototype):
//   pattern A, generar_certificado_documento: nombre = full name, apellidoPaterno = CURP,
//     apellidoMaterno = enrollment number, matricula = program, curso = "Certificado <type>: <title>",
//     fechaEmision = dd/mm/yyyy, id = Unix timestamp.
//   pattern B, emitir_certificado_para_documento: name parts, enrollment number, curso = document title.
// All names and CURPs are fictitious.
const NOMBRES = ["María Fernanda", "José Luis", "Ana Karen", "Juan Carlos", "Diana Laura", "Luis Ángel",
  "Brenda Itzel", "Miguel Ángel", "Karla Daniela", "Jorge Alberto"];
const AP_PAT = ["López", "Martínez", "Sánchez", "Gómez", "Torres", "Reyes", "Jiménez", "Ruiz", "Ortiz", "Chávez"];
const AP_MAT = ["Hernández", "Ramírez", "Cruz", "Flores", "Morales", "Vázquez", "Castillo", "Domínguez", "Mendoza", "Rojas"];
const CARRERAS = ["Ingeniería en Sistemas Computacionales", "Ingeniería Industrial", "Ingeniería en Administración",
  "Ingeniería Informática", "Ingeniería en Ciencia de Datos"];
const DOCS = [["certificado", "Certificado de estudios"], ["constancia", "Constancia de estudios"],
  ["historial", "Historial académico"], ["boleta", "Boleta de calificaciones 2026-1"],
  ["liberacion_ss", "Liberación de servicio social"]];
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function curp(i) {
  const L = (k) => LETTERS[(i * 7 + k * 11) % 26];
  const yy = String(2 + (i % 5)).padStart(2, "0");
  const mm = String(1 + (i % 12)).padStart(2, "0");
  const dd = String(1 + (i % 28)).padStart(2, "0");
  return `${L(1)}${L(2)}${L(3)}${L(4)}0${yy.slice(-1)}${mm}${dd}${i % 2 ? "H" : "M"}MC${L(5)}${L(6)}${L(7)}0${i % 10}`;
}

function record(i, baseTs = 1792200000) {
  const nombre = NOMBRES[i % 10];
  const ap = AP_PAT[(i * 3) % 10];
  const am = AP_MAT[(i * 7) % 10];
  const matricula = String(236022000 + i);
  const carrera = CARRERAS[i % CARRERAS.length];
  const [tipo, titulo] = DOCS[i % DOCS.length];
  const fecha = `${String(1 + (i % 28)).padStart(2, "0")}/10/2026`;
  return {
    A: [baseTs + i, `${nombre} ${ap} ${am}`, curp(i), matricula, carrera, `Certificado ${tipo}: ${titulo}`, fecha],
    B: [1000 + i, nombre, ap, am, matricula, titulo, fecha],
  };
}

module.exports = { record, curp };
