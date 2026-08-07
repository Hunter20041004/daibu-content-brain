    <script>
      (() => {
        const storageKey = "vt-comments-" + location.pathname;
        const quoteLimit = 80;
        let comments = JSON.parse(localStorage.getItem(storageKey) || "[]");
        let selection = null;
        const byId = (id) => document.getElementById(id);
        const trigger = byId("vt-comment-trigger");
        const popup = byId("vt-comment-popup");
        const popupQuote = byId("vt-popup-quote");
        const popupTextarea = byId("vt-popup-textarea");
        const commentPill = byId("vt-comment-pill");
        const count = byId("vt-count");
        const list = byId("vt-comment-list");
        const listItems = byId("vt-comment-list-items");

        window.vtCollectComments = function () {
          if (!comments.length) return "";
          return "\n\n---\n\n" + comments.map((comment) => {
            const quote = comment.quote.length > quoteLimit ? comment.quote.slice(0, quoteLimit) + "…" : comment.quote;
            return `@評論「${quote}」\n  → ${comment.body}`;
          }).join("\n\n");
        };

        function handleSelection(event) {
          if (event.target.closest(".vt-comment-popup,.vt-comment-trigger,.vt-comment-pill,.vt-comment-list,button,input,select,textarea")) return;
          setTimeout(() => {
            const currentSelection = getSelection();
            const text = currentSelection.toString().trim();
            if (!text || text.length < 2 || !currentSelection.rangeCount) {
              trigger.style.display = "none";
              return;
            }
            const range = currentSelection.getRangeAt(0);
            const box = range.getBoundingClientRect();
            selection = { text, range: range.cloneRange() };
            trigger.style.display = "inline-flex";
            trigger.style.top = Math.max(8, box.top - 42) + "px";
            trigger.style.left = Math.max(8, box.left + box.width / 2 - 40) + "px";
          }, 10);
        }

        function openPopup() {
          if (!selection) return;
          popupQuote.textContent = selection.text.length > quoteLimit ? selection.text.slice(0, quoteLimit) + "…" : selection.text;
          popupTextarea.value = "";
          const triggerBox = trigger.getBoundingClientRect();
          let left = triggerBox.left;
          if (left + 340 > innerWidth - 16) left = innerWidth - 356;
          let top = triggerBox.bottom + 6;
          if (top + 220 > innerHeight) top = triggerBox.top - 230;
          popup.style.left = Math.max(8, left) + "px";
          popup.style.top = Math.max(8, top) + "px";
          trigger.style.display = "none";
          popup.style.display = "block";
          setTimeout(() => popupTextarea.focus(), 50);
        }

        function closePopup() {
          popup.style.display = "none";
          selection = null;
        }

        function persist() {
          localStorage.setItem(storageKey, JSON.stringify(comments));
        }

        function escapeHtml(value) {
          return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
        }

        function deleteComment(id) {
          comments = comments.filter((comment) => comment.id !== id);
          document.querySelectorAll(`mark.vt-comment-mark[data-comment-id="${id}"]`).forEach((mark) => {
            const parent = mark.parentNode;
            while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
            parent.removeChild(mark);
            parent.normalize();
          });
          persist();
          renderComments();
        }

        function renderComments() {
          count.textContent = comments.length;
          commentPill.classList.toggle("is-active", comments.length > 0);
          if (!comments.length) list.classList.remove("is-open");
          listItems.innerHTML = comments.map((comment) => {
            const quote = comment.quote.length > 60 ? comment.quote.slice(0, 60) + "…" : comment.quote;
            return `<div class="vt-comment-item" data-id="${comment.id}"><div class="item-quote">「${escapeHtml(quote)}」</div><div class="item-body">${escapeHtml(comment.body)}</div><button class="item-del" data-del="${comment.id}" type="button">刪除</button></div>`;
          }).join("");
          listItems.querySelectorAll("[data-del]").forEach((button) => button.addEventListener("click", () => deleteComment(button.dataset.del)));
        }

        function saveComment() {
          const body = popupTextarea.value.trim();
          if (!body || !selection) return closePopup();
          const id = "c-" + Date.now();
          try {
            const mark = document.createElement("mark");
            mark.className = "vt-comment-mark";
            mark.dataset.commentId = id;
            selection.range.surroundContents(mark);
          } catch (error) {
            console.debug("選取範圍跨越多個元素，只保存評論文字。", error);
          }
          comments.push({ id, quote: selection.text, body, ts: Date.now() });
          persist();
          renderComments();
          closePopup();
          getSelection().removeAllRanges();
        }

        document.addEventListener("mouseup", handleSelection);
        document.addEventListener("touchend", handleSelection);
        trigger.addEventListener("click", openPopup);
        byId("vt-popup-cancel").addEventListener("click", closePopup);
        byId("vt-popup-send").addEventListener("click", saveComment);
        popupTextarea.addEventListener("keydown", (event) => {
          if (event.isComposing || event.keyCode === 229) return;
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
            event.preventDefault();
            event.stopPropagation();
            saveComment();
          }
          if (event.key === "Escape") closePopup();
        });
        commentPill.addEventListener("click", () => list.classList.toggle("is-open"));
        byId("vt-clear-all").addEventListener("click", () => {
          if (!comments.length || !confirm("確定清除全部 " + comments.length + " 條評論？")) return;
          document.querySelectorAll("mark.vt-comment-mark").forEach((mark) => {
            const parent = mark.parentNode;
            while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
            parent.removeChild(mark);
            parent.normalize();
          });
          comments = [];
          persist();
          renderComments();
        });
        byId("vt-copy-fallback").addEventListener("click", (event) => {
          if (!comments.length) return;
          const text = window.vtCollectComments().replace(/^\n\n---\n\n/, "");
          const button = event.currentTarget;
          const original = button.textContent;
          const done = () => {
            button.textContent = "已複製";
            setTimeout(() => { button.textContent = original; }, 2000);
          };
          navigator.clipboard.writeText(text).then(done).catch(() => {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            textarea.remove();
            done();
          });
        });
        setTimeout(() => {
          if (typeof window.vtBuildDecisionExport === "function") document.body.classList.add("vt-has-existing-export");
        }, 100);
        document.addEventListener("click", (event) => {
          if (popup.style.display === "block" && !event.target.closest(".vt-comment-popup,.vt-comment-trigger")) closePopup();
        });
        renderComments();
      })();
    </script>
