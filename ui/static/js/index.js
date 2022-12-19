$(() => {
  initLadder();

  $("#ladder").on("auxclick", e => {
    scrollY = 0;
    recalcBbo();
    onBook(lastBook);
  });

  $("#ladder").on("wheel", e => {
    scrollY += e.originalEvent.deltaY / 100 * -1;
    onBook(lastBook);
  });

  $(".orders").on("click", e => {
    const price = parseFloat(e.target.nextSibling.nextSibling.textContent);
    const workingOrder = workingOrders.find(o => o.price == price);
    if (workingOrder != null) {
      ws.send(JSON.stringify({ topic: "cancel_order", order_id: workingOrder['order_id'] }));
    }
  });

  $(".bid").on("click", e => {
    const price = parseFloat(e.target.nextSibling.textContent);
    ws.send(JSON.stringify({ topic: "new_order_single", side: "b", price: price }));
  });

  $(".ask").on("click", e => {
    const price = parseFloat(e.target.previousSibling.textContent);
    ws.send(JSON.stringify({ topic: "new_order_single", side: "s", price: price }));
  });

  $(".displayPrice").on("click", e => {
    const price = parseFloat(e.target.textContent);

  });

})

let workingOrders = [];
let tradeUpdates = [];
let position;
let totalPnl = 0;
let lastBook;
let bestBid;
let bestAsk;
let bidVwap;
let askVwap;
let scrollY = 0;

//  overwritten on symbol config
let tickSize = 0.01;
let tickToFixed = 1;

function initLadder() {
  const table = $("#ladder")[0];
  if (table.rows.length == 1) {
    for (let x=0; x<40; x++) {
        const row = table.insertRow(x);
        orders = row.insertCell(0);
        orders.width = "20%"
        orders.classList.add("orders");

        bids = row.insertCell(1);
        bids.width = "20%"
        bids.classList.add("bid");

        price = row.insertCell(2);
        price.width = "20%"
        price.classList.add("displayPrice");

        asks = row.insertCell(3);
        asks.width = "20%"
        asks.classList.add("ask");

        trades = row.insertCell(4);
        trades.width = "20%"
        trades.classList.add("trade");
      }
  }
  else if (bestBid != null && bestAsk != null) {
    while (bestAsk - bestBid > tickSize * 2) {
      bestBid += tickSize;
    }

    for (let x=0; x<20; x++) {
      const row = table.rows[19 - x];
      const tds = row.getElementsByTagName('td');
      tds[0].textContent = "";
      tds[1].textContent = "";
      tds[2].textContent = (bestAsk + scrollY * tickSize + tickSize * x).toFixed(tickToFixed);
      tds[3].textContent = "";
      tds[4].textContent = "";
    }

    for (let x=0; x<20; x++) {
      const row = table.rows[x + 20];
      const tds = row.getElementsByTagName('td');
      tds[0].textContent = "";
      tds[1].textContent = "";
      tds[2].textContent = (bestBid + scrollY * tickSize - tickSize * x).toFixed(tickToFixed);
      tds[3].textContent = "";
      tds[4].textContent = "";
    }
  }
}

function updateLadderQuote(quote, is_bid) {
  const table = $("#ladder")[0];
  const priceEle = $(".displayPrice").filter(
    (_, val) => val.textContent == quote.price.toFixed(tickToFixed)
  );
  if (priceEle.length > 0) {
    qtyCell = is_bid ? 1 : 3;
    const children = priceEle[0].parentNode.children;
    children[qtyCell].textContent = quote.volume.toFixed(5);
  }
}

function updateLadderTrade(trade) {
  const table = $("#ladder")[0];
  const priceEle = $(".displayPrice").filter(
    (_, val) => val.textContent == trade.price.toFixed(tickToFixed)
  );
  if (priceEle.length > 0) {
    const children = priceEle[0].parentNode.children;
    if (children[4].textContent != "") {
      children[4].textContent = (parseFloat(children[4].textContent) + trade.volume).toFixed(5);
    }
    else {
      children[4].textContent = trade.volume.toFixed(5);
    }
  }
}

function recalcBbo() {
    bestAsk = Math.min(...lastBook["asks"].map(val => val.price));
    bestBid = Math.max(...lastBook["bids"].map(val => val.price));
}

function getMaxVolumeQuote(quotes) {
    const max_ = Math.max(...quotes.map(val => val.volume));
    return quotes.find(q => q.volume == max_);
}

function getTotalVolume(quotes) {
  let sum_ = 0;
  for (let quote of quotes) {
    sum_ += quote.volume;
  }
  return sum_;
}

function onBook(js) {
  lastBook = js;

  if (bestAsk == null || bestBid == null) {
    recalcBbo();
  }
  initLadder();

  for (let x=0; x<js["asks"].length; x++) {
    ask = js["asks"][x];
    updateLadderQuote(ask, false);
  }

  for (let x=0; x<js["bids"].length; x++) {
    bid = js["bids"][x];
    updateLadderQuote(bid, true);
  }

  const baVolume = js["asks"][9].volume;
  const baPrice = js["asks"][9].price;
  const bbVolume = js["bids"][0].volume;
  const bbPrice = js["bids"][0].price;

  $("#bestAsk").text(`Ask: ${baVolume.toFixed(3)} @ ${baPrice.toFixed(tickToFixed)}`);
  $("#bestBid").text(`Bid: ${bbVolume.toFixed(3)} @ ${bbPrice.toFixed(tickToFixed)}`);

  const spread = baPrice - bbPrice;
  $("#spread").text(`Spread: ${(spread).toFixed(tickToFixed)}`);

  if (spread < tickSize * 2) {
    const juice = (baVolume / bbVolume).toFixed(5);
    if (juice < 0.1 && bbVolume >= 5) {
      $("#strategyIcon").html("&#128994;");
    }
    else if (juice > 10 && baVolume >= 5) {
      $("#strategyIcon").html("&#128308;");
    }
    else {
      $("#strategyIcon").html("");
    }
    $("#strategy").text(`Ratio: ${juice}`);
  }
  else {
    $("#strategy").text("");
    $("#strategyIcon").html("");
  }

  const highLean = getMaxVolumeQuote(js["asks"]);
  const askVolume = getTotalVolume(js["asks"]);
  const lowLean = getMaxVolumeQuote(js["bids"]);
  const bidVolume = getTotalVolume(js["bids"]);
  const diff = (highLean.price - lowLean.price).toFixed(tickToFixed);
  $("#highLean").text(
    `High Lean: ${highLean.volume.toFixed(3)} (${(highLean.volume / askVolume * 100).toFixed(1)}%) @ ${highLean.price} (${diff})`
  );

  $("#lowLean").text(
    `Low Lean: ${lowLean.volume.toFixed(3)} (${(lowLean.volume / bidVolume * 100).toFixed(1)}%) @ ${lowLean.price} (${diff})`
  );

  if (position != null) {
    if (position["qty"] == 0) {
      $("#position").text("");
      $("#pnl").text("");
    }
    else {
      $("#position").text(
        `Position: ${position["qty"].toFixed(5)} @ ${position["avg_price"].toFixed(tickToFixed)}`
      )
      updatePnl();
    }
  }
  // $("#totalPnl").text(`Total Pnl: ${totalPnl}`);
  updateTrades();
  updateWorkingOrders();
}

function updatePnl() {
  let pnl;
  if (position["qty"] < 0) {
    pnl = (position["avg_price"] - lastBook["asks"][9].price) * -1 * position["qty"];
  }
  else {
    pnl = (lastBook["bids"][0].price - position["avg_price"]) * position["qty"];
  }
  $("#pnl").text(`Pnl: ${pnl.toFixed(5)}`);
}

function onTrade(js) {
  tradeUpdates.push(js);
  $("#lastTrade").text(`Last Trade: ${js["volume"].toFixed(5)} @ ${js["price"].toFixed(tickToFixed)}`);
  updateTrades();
}

function updateTrades() {
  for (let trade of tradeUpdates) {
    updateLadderTrade(trade);
  }
}

function onWorkingOrder(js) {
  workingOrders = js;
  updateWorkingOrders();
}

function updateWorkingOrders() {
  const table = $("#ladder")[0];
  let text = "";
  for (let order of workingOrders) {
    const priceEle = $(".displayPrice").filter(
      (_, val) => val.textContent == order.price.toFixed(tickToFixed)
    );
    if (priceEle.length > 0) {
      const children = priceEle[0].parentNode.children;
      let qty = 0;
      if (children[0].textContent != "") {
         qty = parseFloat(children[0].textContent) + order.qty;
         children[0].textContent = qty.toFixed(5);
      }
      else {
        qty = order.qty;
        children[0].textContent = qty.toFixed(5);
      }
    }
    text += `Working: ${order.qty.toFixed(5)} @ ${order.price.toFixed(tickToFixed)}`;
    text += '<br>';
  }
  $("#workingOrders").html(text);
}

function onVwap(js) {
  askVwap = js[0];
  let askText = `Vwap: ${js[0]['volume'].toFixed(3)} @ ${js[0]['price'].toFixed(tickToFixed)}`;
  askText += ` (-${maxPriceDiff(lastBook['asks'], false)})`
  $("#askVwap").text(askText)

  bidVwap = js[1];
  let bidText = `Vwap: ${js[1]['volume'].toFixed(3)} @ ${js[1]['price'].toFixed(tickToFixed)}`
  bidText += ` (-${maxPriceDiff(lastBook['bids'], true)})`
  $("#bidVwap").text(bidText)
}

function maxPriceDiff(quotes, is_bid) {
  max_ = 0;
  if (!is_bid) {
    for (let x=9; x>7; x--) {
      const diff = Math.abs(parseFloat(quotes[x].price) - parseFloat(quotes[x - 1].price));
      if (diff > max_) {
        max_ = diff;
      }
    }
  }
  else {
    for (let x=0; x<2; x++) {
      const diff = Math.abs(parseFloat(quotes[x + 1].price) - parseFloat(quotes[x].price));
      if (diff > max_) {
        max_ = diff;
      }
    }
  }
  return max_.toFixed(tickToFixed);
}

function onOrderStatus(js) {
  $("#lastOrderStatus").text(
    `${js["status"]}: ${js["desc"]} / ${js["errorMessage"]}`
  )
}

function onSubscription(js) {
  let text = $("#subscriptions").text();
  text += `${js["channelName"]}: ${js["pair"]} (${js["status"]})`
  $("#subscriptions").text(text);
}

function onSystemStatus(js) {
  $("#systemStatus").text(`${js["event"]}: ${js["status"]}`);
}

function onSymbolConfig(js) {
  tickSize = js["tick_size"];
  tickToFixed = 1;
  let count = 10;
  while (tickSize * count < 1) {
    count  *= 10;
    tickToFixed++;
  }
}

function onPosition(js) {
  position = js;
}

const ws = new WebSocket("ws://127.0.0.1:8889");
ws.onmessage = js => {
  data = JSON.parse(js.data)
  const topic = data['py/object']
  if (topic == 'app.book.Book') {
    data["asks"].reverse();
    onBook(data);
  }
  else if (topic == 'common.Trade') {
    onTrade(data);
  }
  else if (topic == 'common.Position') {
    onPosition(data);
  }
  else if (topic == 'kraken.messages.SubscriptionStatus') {
    onSubscription(data);
  }
  else if (topic == 'kraken.messages.SystemStatus') {
    onSystemStatus(data);
  }
  else if (topic == "kraken.messages.OrderStatus") {
    onOrderStatus(data);
  }
  else if (topic == 'kraken.SymbolConfig') {
    onSymbolConfig(data);
  }
  else if (js.data != "{}" && Array.isArray(Object.values(data))){
    if (data[0] != null && data[0]['py/object'] == 'common.Quote') {
      onVwap(data);
    }
    else {
      onWorkingOrder(Object.values(data));
    }
  }
  else if (js.data == "{}") {
    onWorkingOrder(Object.values(data));
  }
  else {
    console.log(`unknown topic: ${data}`);
  }
}
