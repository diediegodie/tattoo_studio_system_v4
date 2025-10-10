(function () {
  const monthNames = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Março",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro"
  };

  const feedbackStates = ["info", "success", "warning", "error", "loading"];
  const currencyFormatter = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
  });
  const dateFormatter = new Intl.DateTimeFormat("pt-BR");

  let formElement = null;
  let feedbackElement = null;
  let resultsContainer = null;

  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return "";
    }

    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalizeText(value, fallback = "N/A") {
    if (value === null || value === undefined || value === "") {
      return fallback;
    }
    return value;
  }

  function formatCurrency(value) {
    if (value === null || value === undefined || value === "") {
      return currencyFormatter.format(0);
    }

    const number = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(number)) {
      return String(value);
    }

    return currencyFormatter.format(number);
  }

  function formatDate(value) {
    if (!value) {
      return "N/A";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }

    return dateFormatter.format(date);
  }

  function setFeedback(message, state = "info") {
    if (!feedbackElement) {
      if (state === "error") {
        window.notifyError ? window.notifyError(message) : console.error(message);
      } else if (state === "warning") {
        window.notifyWarning ? window.notifyWarning(message) : console.warn(message);
      } else {
        console.log(message);
      }
      return;
    }

    feedbackStates.forEach((feedbackState) => {
      feedbackElement.classList.remove(`is-${feedbackState}`);
    });

    if (!feedbackStates.includes(state)) {
      state = "info";
    }

    feedbackElement.classList.add(`is-${state}`);
    feedbackElement.textContent = message;
  }

  function clearResults() {
    if (resultsContainer) {
      resultsContainer.innerHTML = "";
      resultsContainer.dataset.state = "empty";
    }
  }

  function buildTableSection({
    title,
    columns,
    rows,
    emptyMessage,
    headerLevel = "h3",
    headerClass = "major",
    sectionClass = ""
  }) {
    const sectionTitle = escapeHtml(title);
    const headerTag = headerLevel === "h2" ? "h2" : "h3";
    const sectionClasses = ["extrato-section"];

    if (sectionClass) {
      sectionClasses.push(sectionClass);
    }

    const sectionHeaderHtml = `
      <header class="${escapeHtml(headerClass)}">
        <${headerTag}>${sectionTitle}</${headerTag}>
      </header>
    `;

    if (!Array.isArray(rows) || rows.length === 0) {
      return `
        <section class="${sectionClasses.join(" ")}">
          ${sectionHeaderHtml}
          <p class="extrato-empty">${escapeHtml(emptyMessage)}</p>
        </section>
      `;
    }

    const tableHeaderCells = columns
      .map((column) => `<th>${escapeHtml(column.header)}</th>`)
      .join("");

    const tableBodyRows = rows
      .map((row) => {
        const cells = columns
          .map((column) => {
            const value = column.render ? column.render(row) : row[column.key];
            return `<td>${escapeHtml(normalizeText(value))}</td>`;
          })
          .join("");

        return `<tr>${cells}</tr>`;
      })
      .join("");

    return `
      <section class="${sectionClasses.join(" ")}">
        ${sectionHeaderHtml}
        <div class="table-wrapper">
          <table>
            <thead><tr>${tableHeaderCells}</tr></thead>
            <tbody>${tableBodyRows}</tbody>
          </table>
        </div>
      </section>
    `;
  }

  function buildMonthlyTotalsSection(totais) {
    if (!totais || typeof totais !== "object") {
      return "";
    }

    const metrics = [
      ["Receita Total (Bruta)", totais.receita_total],
      ["Comissões Totais", totais.comissoes_total],
      ["Despesas (Gastos)", totais.despesas_total],
      ["Receita Líquida (Bruta - Comissões)", totais.receita_liquida]
    ];

    const rowsHtml = metrics
      .map(
        ([label, value]) =>
          `<tr><td>${escapeHtml(label)}</td><td>${formatCurrency(value)}</td></tr>`
      )
      .join("");

    return `
      <section class="extrato-section extrato-section--totais">
        <header class="major"><h2>Totais do Mês Atual</h2></header>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr><th>Métrica</th><th>Valor</th></tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div>
      </section>
    `;
  }

  function renderResults(data) {
    if (!resultsContainer) {
      return;
    }

    const safeData = data || {};
    const pagamentos = Array.isArray(safeData.pagamentos) ? safeData.pagamentos : [];
    const comissoes = Array.isArray(safeData.comissoes) ? safeData.comissoes : [];
    const sessoes = Array.isArray(safeData.sessoes) ? safeData.sessoes : [];
    const gastos = Array.isArray(safeData.gastos) ? safeData.gastos : [];
    const totais =
      safeData.totais && typeof safeData.totais === "object" ? safeData.totais : null;

    const sections = [];

    sections.push(
      buildTableSection({
        title: "Pagamentos",
        rows: pagamentos,
        emptyMessage: "Nenhum pagamento encontrado.",
        headerLevel: "h2",
        sectionClass: "extrato-section--pagamentos",
        columns: [
          {
            header: "Data",
            render: (row) => formatDate(row.data)
          },
          {
            header: "Cliente",
            render: (row) => row.cliente_name || "Não informado"
          },
          {
            header: "Artista",
            render: (row) => row.artista_name || ""
          },
          {
            header: "Valor",
            render: (row) => formatCurrency(row.valor)
          },
          {
            header: "Forma de pagamento",
            render: (row) => row.forma_pagamento || ""
          },
          {
            header: "Observações",
            render: (row) => row.observacoes || ""
          }
        ]
      })
    );

    sections.push(
      buildTableSection({
        title: "Comissões",
        rows: comissoes,
        emptyMessage: "Nenhuma comissão encontrada.",
        headerLevel: "h2",
        sectionClass: "extrato-section--comissoes",
        columns: [
          {
            header: "Data",
            render: (row) => formatDate(row.created_at)
          },
          {
            header: "Artista",
            render: (row) => row.artista_name || ""
          },
          {
            header: "Cliente",
            render: (row) => row.cliente_name || "Não informado"
          },
          {
            header: "Valor total",
            render: (row) => formatCurrency(row.pagamento_valor)
          },
          {
            header: "Comissão",
            render: (row) => formatCurrency(row.valor)
          },
          {
            header: "Observações",
            render: (row) => row.observacoes || ""
          }
        ]
      })
    );

    sections.push(
      buildTableSection({
        title: "Sessões realizadas",
        rows: sessoes,
        emptyMessage: "Nenhuma sessão encontrada.",
        headerLevel: "h2",
        sectionClass: "extrato-section--sessoes",
        columns: [
          {
            header: "Data",
            render: (row) => formatDate(row.data)
          },
          {
            header: "Cliente",
            render: (row) => row.cliente_name || "Não informado"
          },
          {
            header: "Artista",
            render: (row) => row.artista_name || ""
          },
          {
            header: "Valor",
            render: (row) => formatCurrency(row.valor)
          },
          {
            header: "Observações",
            render: (row) => row.observacoes || ""
          }
        ]
      })
    );

    if (totais && Array.isArray(totais.por_artista) && totais.por_artista.length > 0) {
      sections.push(
        buildTableSection({
          title: "Comissões por Artista",
          rows: totais.por_artista,
          emptyMessage: "Sem dados de comissões por artista.",
          headerLevel: "h3",
          sectionClass: "extrato-section--totais-artista",
          columns: [
            {
              header: "Artista",
              render: (row) => row.artista || ""
            },
            {
              header: "Receita Gerada",
              render: (row) => formatCurrency(row.receita)
            },
            {
              header: "Comissão",
              render: (row) => formatCurrency(row.comissao)
            }
          ]
        })
      );
    }

    if (
      totais &&
      Array.isArray(totais.por_forma_pagamento) &&
      totais.por_forma_pagamento.length > 0
    ) {
      sections.push(
        buildTableSection({
          title: "Receita por Forma de Pagamento",
          rows: totais.por_forma_pagamento,
          emptyMessage: "Sem dados de receita por forma de pagamento.",
          headerLevel: "h3",
          sectionClass: "extrato-section--totais-forma",
          columns: [
            {
              header: "Forma de Pagamento",
              render: (row) => row.forma || ""
            },
            {
              header: "Total",
              render: (row) => formatCurrency(row.total)
            }
          ]
        })
      );
    }

    if (gastos.length > 0) {
      sections.push(
        buildTableSection({
          title: "Gastos do Mês",
          rows: gastos,
          emptyMessage: "Nenhum gasto encontrado.",
          headerLevel: "h3",
          sectionClass: "extrato-section--gastos",
          columns: [
            {
              header: "Data",
              render: (row) => formatDate(row.data)
            },
            {
              header: "Valor",
              render: (row) => formatCurrency(row.valor)
            },
            {
              header: "Descrição",
              render: (row) => row.descricao || ""
            },
            {
              header: "Forma de Pagamento",
              render: (row) => row.forma_pagamento || ""
            }
          ]
        })
      );
    }

    const totalsSection = buildMonthlyTotalsSection(totais);
    if (totalsSection) {
      sections.push(totalsSection);
    }

    resultsContainer.innerHTML = sections.join("");
    resultsContainer.dataset.state = "loaded";

    if (typeof resultsContainer.scrollIntoView === "function") {
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!formElement) {
      return;
    }

    const mesRaw = formElement.querySelector("#mes")?.value || "";
    const anoRaw = formElement.querySelector("#ano")?.value || "";

    if (!mesRaw || !anoRaw) {
      setFeedback("Por favor, selecione o mês e o ano.", "warning");
      clearResults();
      return;
    }

    const mes = mesRaw.padStart(2, "0");
    const ano = anoRaw;
    const periodoLabel = `${monthNames[mes] || mes}/${ano}`;

    setFeedback(`Carregando extrato de ${periodoLabel}...`, "loading");
    clearResults();

    const params = new URLSearchParams({ mes, ano });

    let response;
    try {
      response = await fetch(`/extrato/api?${params.toString()}`, {
        headers: {
          Accept: "application/json"
        }
      });
    } catch (networkError) {
      console.error("Falha de rede ao carregar extrato", networkError);
      setFeedback("Erro de conexão. Verifique sua internet e tente novamente.", "error");
      return;
    }

    let payload;
    try {
      payload = await response.json();
    } catch (parseError) {
      console.error("Não foi possível interpretar a resposta do extrato", parseError);
      setFeedback("Resposta inválida do servidor. Tente novamente mais tarde.", "error");
      return;
    }

    if (!response.ok || payload.success === false) {
      const defaultNotFound = "Nenhum extrato encontrado para este mês.";
      const message = payload && payload.message ? payload.message : defaultNotFound;
      const state = response.status === 404 ? "warning" : "error";
      setFeedback(message || defaultNotFound, state);
      clearResults();
      return;
    }

    if (!payload.data) {
      setFeedback("Nenhum dado retornado pelo servidor.", "warning");
      clearResults();
      return;
    }

    renderResults(payload.data);
    setFeedback(`Extrato de ${periodoLabel} carregado com sucesso.`, "success");
  }

  function initializeExtrato() {
    formElement = document.getElementById("extrato-form");
    feedbackElement = document.getElementById("extrato-feedback");
    resultsContainer = document.getElementById("extrato-results");

    if (!formElement || !resultsContainer) {
      return;
    }

    const monthSelect = formElement.querySelector("#mes");
    const yearSelect = formElement.querySelector("#ano");
    const initialMes = formElement.dataset.initialMes || "";
    const initialAno = formElement.dataset.initialAno || "";

    if (initialMes && monthSelect) {
      monthSelect.value = initialMes;
    }

    if (initialAno && yearSelect) {
      yearSelect.value = initialAno;
    }

    if (feedbackElement) {
      const bootstrapState = feedbackElement.dataset.bootstrapState || "info";
      const bootstrapMessage = feedbackElement.dataset.bootstrapMessage;
      if (bootstrapMessage) {
        setFeedback(bootstrapMessage, bootstrapState);
      }
    }

    if (resultsContainer) {
      const bootstrapPayload = resultsContainer.dataset.bootstrap;
      if (bootstrapPayload) {
        try {
          const parsedPayload = JSON.parse(bootstrapPayload);
          if (parsedPayload && typeof parsedPayload === "object") {
            renderResults(parsedPayload);
            resultsContainer.dataset.state = "loaded";
          }
        } catch (error) {
          console.error("Bootstrap do extrato inválido", error);
          setFeedback(
            "Erro ao carregar dados iniciais do extrato.",
            "error"
          );
          clearResults();
        }
      } else if (
        feedbackElement &&
        ["warning", "error"].includes(
          feedbackElement.dataset.bootstrapState || ""
        )
      ) {
        resultsContainer.dataset.state = "empty";
      }
    }

    formElement.addEventListener("submit", handleSubmit);
  }

  if (document.readyState === "loading" || document.readyState === "interactive") {
    document.addEventListener("DOMContentLoaded", initializeExtrato);
  } else {
    initializeExtrato();
  }
})();
