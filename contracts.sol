# Smart Contract Templates for Martius Network
# 10 different contract types with interactive functions

CONTRACTS = {
    "voting": {
        "name": "Voting Contract",
        "code": '''
pragma solidity ^0.8.19;

contract Voting {
    struct Proposal {
        string description;
        uint256 yesVotes;
        uint256 noVotes;
        bool active;
        mapping(address => bool) hasVoted;
    }
    
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    address public owner;
    
    event ProposalCreated(uint256 indexed proposalId, string description);
    event VoteCast(uint256 indexed proposalId, address indexed voter, bool vote);
    
    constructor() {
        owner = msg.sender;
        proposalCount = 0;
    }
    
    function createProposal(string memory _description) external {
        require(msg.sender == owner, "Only owner can create proposals");
        
        proposals[proposalCount].description = _description;
        proposals[proposalCount].active = true;
        
        emit ProposalCreated(proposalCount, _description);
        proposalCount++;
    }
    
    function vote(uint256 _proposalId, bool _vote) external {
        require(_proposalId < proposalCount, "Proposal does not exist");
        require(proposals[_proposalId].active, "Proposal is not active");
        require(!proposals[_proposalId].hasVoted[msg.sender], "Already voted");
        
        proposals[_proposalId].hasVoted[msg.sender] = true;
        
        if (_vote) {
            proposals[_proposalId].yesVotes++;
        } else {
            proposals[_proposalId].noVotes++;
        }
        
        emit VoteCast(_proposalId, msg.sender, _vote);
    }
    
    function getProposal(uint256 _proposalId) external view returns (string memory description, uint256 yesVotes, uint256 noVotes, bool active) {
        require(_proposalId < proposalCount, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        return (proposal.description, proposal.yesVotes, proposal.noVotes, proposal.active);
    }
}
''',
        "interactions": ["createProposal", "vote", "getProposal"]
    },
    
    "token": {
        "name": "ERC20 Token",
        "code": '''
pragma solidity ^0.8.19;

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract SimpleToken is IERC20 {
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    uint256 private _totalSupply;
    string public name;
    string public symbol;
    uint8 public decimals;
    address public owner;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    
    constructor() {
        name = "MartToken";
        symbol = "MART";
        decimals = 18;
        _totalSupply = 1000000 * 10**decimals;
        owner = msg.sender;
        _balances[msg.sender] = _totalSupply;
        emit Transfer(address(0), msg.sender, _totalSupply);
    }
    
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address to, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }
    
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) external override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= amount, "Transfer amount exceeds allowance");
        
        _transfer(from, to, amount);
        _approve(from, msg.sender, currentAllowance - amount);
        
        return true;
    }
    
    function mint(address to, uint256 amount) external {
        require(msg.sender == owner, "Only owner can mint");
        _totalSupply += amount;
        _balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }
    
    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "Transfer from zero address");
        require(to != address(0), "Transfer to zero address");
        require(_balances[from] >= amount, "Transfer amount exceeds balance");
        
        _balances[from] -= amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "Approve from zero address");
        require(spender != address(0), "Approve to zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
}
''',
        "interactions": ["transfer", "mint", "balanceOf"]
    },
    
    "nft": {
        "name": "NFT Contract",
        "code": '''
pragma solidity ^0.8.19;

interface IERC165 {
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

interface IERC721 {
    function balanceOf(address owner) external view returns (uint256 balance);
    function ownerOf(uint256 tokenId) external view returns (address owner);
    function safeTransferFrom(address from, address to, uint256 tokenId, bytes calldata data) external;
    function safeTransferFrom(address from, address to, uint256 tokenId) external;
    function transferFrom(address from, address to, uint256 tokenId) external;
    function approve(address to, uint256 tokenId) external;
    function setApprovalForAll(address operator, bool approved) external;
    function getApproved(uint256 tokenId) external view returns (address operator);
    function isApprovedForAll(address owner, address operator) external view returns (bool);
}

contract SimpleNFT is IERC165, IERC721 {
    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => address) private _tokenApprovals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    
    uint256 public nextTokenId = 1;
    address public owner;
    string public name;
    string public symbol;
    
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);
    
    constructor() {
        name = "MartNFT";
        symbol = "MNFT";
        owner = msg.sender;
    }
    
    function supportsInterface(bytes4 interfaceId) external pure override returns (bool) {
        return interfaceId == type(IERC721).interfaceId || interfaceId == type(IERC165).interfaceId;
    }
    
    function balanceOf(address ownerAddr) external view override returns (uint256) {
        require(ownerAddr != address(0), "Query for zero address");
        return _balances[ownerAddr];
    }
    
    function ownerOf(uint256 tokenId) public view override returns (address) {
        address ownerAddr = _owners[tokenId];
        require(ownerAddr != address(0), "Token does not exist");
        return ownerAddr;
    }
    
    function mint(address to) external returns (uint256) {
        require(msg.sender == owner, "Only owner can mint");
        require(to != address(0), "Mint to zero address");
        
        uint256 tokenId = nextTokenId;
        nextTokenId++;
        
        _balances[to]++;
        _owners[tokenId] = to;
        
        emit Transfer(address(0), to, tokenId);
        return tokenId;
    }
    
    function transferFrom(address from, address to, uint256 tokenId) public override {
        require(_isApprovedOrOwner(msg.sender, tokenId), "Not approved or owner");
        _transfer(from, to, tokenId);
    }
    
    function safeTransferFrom(address from, address to, uint256 tokenId) external override {
        transferFrom(from, to, tokenId);
    }
    
    function safeTransferFrom(address from, address to, uint256 tokenId, bytes calldata) external override {
        transferFrom(from, to, tokenId);
    }
    
    function approve(address to, uint256 tokenId) external override {
        address ownerAddr = ownerOf(tokenId);
        require(to != ownerAddr, "Approval to current owner");
        require(msg.sender == ownerAddr || isApprovedForAll(ownerAddr, msg.sender), "Not approved or owner");
        
        _tokenApprovals[tokenId] = to;
        emit Approval(ownerAddr, to, tokenId);
    }
    
    function getApproved(uint256 tokenId) public view override returns (address) {
        require(_owners[tokenId] != address(0), "Token does not exist");
        return _tokenApprovals[tokenId];
    }
    
    function setApprovalForAll(address operator, bool approved) external override {
        require(operator != msg.sender, "Approve to caller");
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }
    
    function isApprovedForAll(address ownerAddr, address operator) public view override returns (bool) {
        return _operatorApprovals[ownerAddr][operator];
    }
    
    function _isApprovedOrOwner(address spender, uint256 tokenId) internal view returns (bool) {
        address ownerAddr = ownerOf(tokenId);
        return (spender == ownerAddr || getApproved(tokenId) == spender || isApprovedForAll(ownerAddr, spender));
    }
    
    function _transfer(address from, address to, uint256 tokenId) internal {
        require(ownerOf(tokenId) == from, "Transfer from incorrect owner");
        require(to != address(0), "Transfer to zero address");
        
        _tokenApprovals[tokenId] = address(0);
        _balances[from]--;
        _balances[to]++;
        _owners[tokenId] = to;
        
        emit Transfer(from, to, tokenId);
    }
}
''',
        "interactions": ["mint", "transferFrom", "balanceOf"]
    },
    
    "auction": {
        "name": "Auction Contract",
        "code": '''
pragma solidity ^0.8.19;

contract SimpleAuction {
    address public owner;
    address public highestBidder;
    uint256 public highestBid;
    uint256 public auctionEndTime;
    bool public auctionEnded;
    
    mapping(address => uint256) public pendingReturns;
    
    event HighestBidIncreased(address bidder, uint256 amount);
    event AuctionEnded(address winner, uint256 amount);
    
    constructor(uint256 _biddingTime) {
        owner = msg.sender;
        auctionEndTime = block.timestamp + _biddingTime;
        auctionEnded = false;
    }
    
    function bid() external payable {
        require(block.timestamp <= auctionEndTime, "Auction already ended");
        require(msg.value > highestBid, "Bid not high enough");
        
        if (highestBidder != address(0)) {
            pendingReturns[highestBidder] += highestBid;
        }
        
        highestBidder = msg.sender;
        highestBid = msg.value;
        
        emit HighestBidIncreased(msg.sender, msg.value);
    }
    
    function withdraw() external returns (bool) {
        uint256 amount = pendingReturns[msg.sender];
        if (amount > 0) {
            pendingReturns[msg.sender] = 0;
            
            if (!payable(msg.sender).send(amount)) {
                pendingReturns[msg.sender] = amount;
                return false;
            }
        }
        return true;
    }
    
    function endAuction() external {
        require(block.timestamp >= auctionEndTime, "Auction not yet ended");
        require(!auctionEnded, "Auction already ended");
        
        auctionEnded = true;
        emit AuctionEnded(highestBidder, highestBid);
        
        payable(owner).transfer(highestBid);
    }
    
    function getAuctionStatus() external view returns (address, uint256, uint256, bool) {
        return (highestBidder, highestBid, auctionEndTime, auctionEnded);
    }
}
''',
        "interactions": ["bid", "withdraw", "endAuction"]
    },
    
    "multisig": {
        "name": "MultiSig Wallet",
        "code": '''
pragma solidity ^0.8.19;

contract MultiSigWallet {
    event Deposit(address indexed sender, uint256 amount, uint256 balance);
    event SubmitTransaction(address indexed owner, uint256 indexed txIndex, address indexed to, uint256 value, bytes data);
    event ConfirmTransaction(address indexed owner, uint256 indexed txIndex);
    event RevokeConfirmation(address indexed owner, uint256 indexed txIndex);
    event ExecuteTransaction(address indexed owner, uint256 indexed txIndex);
    
    address[] public owners;
    mapping(address => bool) public isOwner;
    uint256 public numConfirmationsRequired;
    
    struct Transaction {
        address to;
        uint256 value;
        bytes data;
        bool executed;
        uint256 numConfirmations;
    }
    
    mapping(uint256 => mapping(address => bool)) public isConfirmed;
    Transaction[] public transactions;
    
    modifier onlyOwner() {
        require(isOwner[msg.sender], "Not owner");
        _;
    }
    
    modifier txExists(uint256 _txIndex) {
        require(_txIndex < transactions.length, "Transaction does not exist");
        _;
    }
    
    modifier notExecuted(uint256 _txIndex) {
        require(!transactions[_txIndex].executed, "Transaction already executed");
        _;
    }
    
    modifier notConfirmed(uint256 _txIndex) {
        require(!isConfirmed[_txIndex][msg.sender], "Transaction already confirmed");
        _;
    }
    
    constructor(address[] memory _owners, uint256 _numConfirmationsRequired) {
        require(_owners.length > 0, "Owners required");
        require(_numConfirmationsRequired > 0 && _numConfirmationsRequired <= _owners.length, "Invalid number of confirmations");
        
        for (uint256 i = 0; i < _owners.length; i++) {
            address owner = _owners[i];
            require(owner != address(0), "Invalid owner");
            require(!isOwner[owner], "Owner not unique");
            
            isOwner[owner] = true;
            owners.push(owner);
        }
        
        numConfirmationsRequired = _numConfirmationsRequired;
    }
    
    receive() external payable {
        emit Deposit(msg.sender, msg.value, address(this).balance);
    }
    
    function submitTransaction(address _to, uint256 _value, bytes memory _data) public onlyOwner {
        uint256 txIndex = transactions.length;
        
        transactions.push(Transaction({
            to: _to,
            value: _value,
            data: _data,
            executed: false,
            numConfirmations: 0
        }));
        
        emit SubmitTransaction(msg.sender, txIndex, _to, _value, _data);
    }
    
    function confirmTransaction(uint256 _txIndex) public onlyOwner txExists(_txIndex) notExecuted(_txIndex) notConfirmed(_txIndex) {
        Transaction storage transaction = transactions[_txIndex];
        transaction.numConfirmations += 1;
        isConfirmed[_txIndex][msg.sender] = true;
        
        emit ConfirmTransaction(msg.sender, _txIndex);
    }
    
    function executeTransaction(uint256 _txIndex) public onlyOwner txExists(_txIndex) notExecuted(_txIndex) {
        Transaction storage transaction = transactions[_txIndex];
        require(transaction.numConfirmations >= numConfirmationsRequired, "Cannot execute transaction");
        
        transaction.executed = true;
        
        (bool success, ) = transaction.to.call{value: transaction.value}(transaction.data);
        require(success, "Transaction failed");
        
        emit ExecuteTransaction(msg.sender, _txIndex);
    }
    
    function getTransactionCount() public view returns (uint256) {
        return transactions.length;
    }
}
''',
        "interactions": ["submitTransaction", "confirmTransaction", "executeTransaction"]
    },
    
    "lottery": {
        "name": "Lottery Contract",
        "code": '''
pragma solidity ^0.8.19;

contract Lottery {
    address public owner;
    address[] public players;
    address public winner;
    uint256 public ticketPrice;
    uint256 public lotteryId;
    bool public lotteryActive;
    
    mapping(uint256 => address) public lotteryHistory;
    
    event PlayerEntered(address indexed player, uint256 lotteryId);
    event WinnerSelected(address indexed winner, uint256 amount, uint256 lotteryId);
    
    constructor() {
        owner = msg.sender;
        lotteryId = 1;
        ticketPrice = 0.01 ether;
        lotteryActive = true;
    }
    
    function enterLottery() public payable {
        require(lotteryActive, "Lottery is not active");
        require(msg.value >= ticketPrice, "Insufficient payment");
        
        players.push(msg.sender);
        emit PlayerEntered(msg.sender, lotteryId);
    }
    
    function getRandomNumber() private view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty, players)));
    }
    
    function pickWinner() public {
        require(msg.sender == owner, "Only owner can pick winner");
        require(players.length > 0, "No players in lottery");
        require(lotteryActive, "Lottery is not active");
        
        uint256 randomIndex = getRandomNumber() % players.length;
        winner = players[randomIndex];
        
        uint256 prize = address(this).balance;
        payable(winner).transfer(prize);
        
        lotteryHistory[lotteryId] = winner;
        emit WinnerSelected(winner, prize, lotteryId);
        
        // Reset for next lottery
        players = new address[](0);
        lotteryId++;
    }
    
    function getPlayers() public view returns (address[] memory) {
        return players;
    }
    
    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }
    
    function setTicketPrice(uint256 _price) public {
        require(msg.sender == owner, "Only owner can set price");
        ticketPrice = _price;
    }
    
    function toggleLottery() public {
        require(msg.sender == owner, "Only owner can toggle lottery");
        lotteryActive = !lotteryActive;
    }
}
''',
        "interactions": ["enterLottery", "pickWinner", "getPlayers"]
    },
    
    "staking": {
        "name": "Staking Contract",
        "code": '''
pragma solidity ^0.8.19;

contract StakingContract {
    address public owner;
    uint256 public totalStaked;
    uint256 public rewardRate = 100; // 1% per year
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardDebt;
    }
    
    mapping(address => Stake) public stakes;
    
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 reward);
    
    constructor() {
        owner = msg.sender;
    }
    
    function stake() external payable {
        require(msg.value > 0, "Cannot stake 0");
        
        if (stakes[msg.sender].amount > 0) {
            uint256 pending = calculateReward(msg.sender);
            if (pending > 0) {
                payable(msg.sender).transfer(pending);
                emit RewardClaimed(msg.sender, pending);
            }
        }
        
        stakes[msg.sender].amount += msg.value;
        stakes[msg.sender].timestamp = block.timestamp;
        stakes[msg.sender].rewardDebt = 0;
        totalStaked += msg.value;
        
        emit Staked(msg.sender, msg.value);
    }
    
    function unstake(uint256 _amount) external {
        require(stakes[msg.sender].amount >= _amount, "Insufficient staked amount");
        
        uint256 pending = calculateReward(msg.sender);
        if (pending > 0) {
            payable(msg.sender).transfer(pending);
            emit RewardClaimed(msg.sender, pending);
        }
        
        stakes[msg.sender].amount -= _amount;
        stakes[msg.sender].timestamp = block.timestamp;
        stakes[msg.sender].rewardDebt = 0;
        totalStaked -= _amount;
        
        payable(msg.sender).transfer(_amount);
        emit Unstaked(msg.sender, _amount);
    }
    
    function claimReward() external {
        uint256 pending = calculateReward(msg.sender);
        require(pending > 0, "No rewards available");
        
        stakes[msg.sender].rewardDebt += pending;
        stakes[msg.sender].timestamp = block.timestamp;
        
        payable(msg.sender).transfer(pending);
        emit RewardClaimed(msg.sender, pending);
    }
    
    function calculateReward(address _user) public view returns (uint256) {
        Stake storage userStake = stakes[_user];
        if (userStake.amount == 0) return 0;
        
        uint256 timeStaked = block.timestamp - userStake.timestamp;
        uint256 reward = (userStake.amount * rewardRate * timeStaked) / (365 days * 10000);
        return reward;
    }
    
    function getStakeInfo(address _user) external view returns (uint256 amount, uint256 timestamp, uint256 pendingReward) {
        Stake storage userStake = stakes[_user];
        return (userStake.amount, userStake.timestamp, calculateReward(_user));
    }
    
    receive() external payable {}
}
''',
        "interactions": ["stake", "unstake", "claimReward"]
    },
    
    "marketplace": {
        "name": "NFT Marketplace",
        "code": '''
pragma solidity ^0.8.19;

contract NFTMarketplace {
    struct Listing {
        address seller;
        address nftContract;
        uint256 tokenId;
        uint256 price;
        bool active;
    }
    
    mapping(uint256 => Listing) public listings;
    uint256 public nextListingId = 1;
    address public owner;
    uint256 public feePercent = 250; // 2.5%
    
    event ItemListed(uint256 indexed listingId, address indexed seller, address nftContract, uint256 tokenId, uint256 price);
    event ItemSold(uint256 indexed listingId, address indexed buyer, uint256 price);
    event ListingCancelled(uint256 indexed listingId);
    
    constructor() {
        owner = msg.sender;
    }
    
    function listItem(address _nftContract, uint256 _tokenId, uint256 _price) external returns (uint256) {
        require(_price > 0, "Price must be greater than 0");
        
        uint256 listingId = nextListingId;
        listings[listingId] = Listing({
            seller: msg.sender,
            nftContract: _nftContract,
            tokenId: _tokenId,
            price: _price,
            active: true
        });
        
        nextListingId++;
        emit ItemListed(listingId, msg.sender, _nftContract, _tokenId, _price);
        return listingId;
    }
    
    function buyItem(uint256 _listingId) external payable {
        Listing storage listing = listings[_listingId];
        require(listing.active, "Listing not active");
        require(msg.value >= listing.price, "Insufficient payment");
        
        uint256 fee = (listing.price * feePercent) / 10000;
        uint256 sellerAmount = listing.price - fee;
        
        listing.active = false;
        
        payable(listing.seller).transfer(sellerAmount);
        payable(owner).transfer(fee);
        
        if (msg.value > listing.price) {
            payable(msg.sender).transfer(msg.value - listing.price);
        }
        
        emit ItemSold(_listingId, msg.sender, listing.price);
    }
    
    function cancelListing(uint256 _listingId) external {
        Listing storage listing = listings[_listingId];
        require(listing.seller == msg.sender, "Not the seller");
        require(listing.active, "Listing not active");
        
        listing.active = false;
        emit ListingCancelled(_listingId);
    }
    
    function updatePrice(uint256 _listingId, uint256 _newPrice) external {
        Listing storage listing = listings[_listingId];
        require(listing.seller == msg.sender, "Not the seller");
        require(listing.active, "Listing not active");
        require(_newPrice > 0, "Price must be greater than 0");
        
        listing.price = _newPrice;
    }
    
    function getListing(uint256 _listingId) external view returns (address, address, uint256, uint256, bool) {
        Listing storage listing = listings[_listingId];
        return (listing.seller, listing.nftContract, listing.tokenId, listing.price, listing.active);
    }
    
    function setFeePercent(uint256 _feePercent) external {
        require(msg.sender == owner, "Only owner");
        require(_feePercent <= 1000, "Fee too high"); // Max 10%
        feePercent = _feePercent;
    }
}
''',
        "interactions": ["listItem", "buyItem", "cancelListing"]
    },
    
    "escrow": {
        "name": "Escrow Contract",
        "code": '''
pragma solidity ^0.8.19;

contract Escrow {
    enum State { Created, Funded, Released, Refunded, Disputed }
    
    struct EscrowTrade {
        address buyer;
        address seller;
        address arbiter;
        uint256 amount;
        State state;
        string description;
    }
    
    mapping(uint256 => EscrowTrade) public trades;
    uint256 public nextTradeId = 1;
    
    event TradeCreated(uint256 indexed tradeId, address buyer, address seller, address arbiter, uint256 amount);
    event TradeFunded(uint256 indexed tradeId);
    event TradeReleased(uint256 indexed tradeId);
    event TradeRefunded(uint256 indexed tradeId);
    event TradeDisputed(uint256 indexed tradeId);
    
    function createTrade(address _seller, address _arbiter, string memory _description) external payable returns (uint256) {
        require(msg.value > 0, "Amount must be greater than 0");
        require(_seller != address(0) && _arbiter != address(0), "Invalid addresses");
        require(_seller != msg.sender, "Seller cannot be buyer");
        
        uint256 tradeId = nextTradeId;
        trades[tradeId] = EscrowTrade({
            buyer: msg.sender,
            seller: _seller,
            arbiter: _arbiter,
            amount: msg.value,
            state: State.Funded,
            description: _description
        });
        
        nextTradeId++;
        emit TradeCreated(tradeId, msg.sender, _seller, _arbiter, msg.value);
        emit TradeFunded(tradeId);
        return tradeId;
    }
    
    function releaseFunds(uint256 _tradeId) external {
        EscrowTrade storage trade = trades[_tradeId];
        require(trade.state == State.Funded, "Trade not funded");
        require(msg.sender == trade.buyer || msg.sender == trade.arbiter, "Unauthorized");
        
        trade.state = State.Released;
        payable(trade.seller).transfer(trade.amount);
        emit TradeReleased(_tradeId);
    }
    
    function refundBuyer(uint256 _tradeId) external {
        EscrowTrade storage trade = trades[_tradeId];
        require(trade.state == State.Funded, "Trade not funded");
        require(msg.sender == trade.seller || msg.sender == trade.arbiter, "Unauthorized");
        
        trade.state = State.Refunded;
        payable(trade.buyer).transfer(trade.amount);
        emit TradeRefunded(_tradeId);
    }
    
    function disputeTrade(uint256 _tradeId) external {
        EscrowTrade storage trade = trades[_tradeId];
        require(trade.state == State.Funded, "Trade not funded");
        require(msg.sender == trade.buyer || msg.sender == trade.seller, "Unauthorized");
        
        trade.state = State.Disputed;
        emit TradeDisputed(_tradeId);
    }
    
    function resolveDispute(uint256 _tradeId, bool _releaseTo) external {
        EscrowTrade storage trade = trades[_tradeId];
        require(trade.state == State.Disputed, "Trade not disputed");
        require(msg.sender == trade.arbiter, "Only arbiter can resolve");
        
        if (_releaseTo) {
            trade.state = State.Released;
            payable(trade.seller).transfer(trade.amount);
            emit TradeReleased(_tradeId);
        } else {
            trade.state = State.Refunded;
            payable(trade.buyer).transfer(trade.amount);
            emit TradeRefunded(_tradeId);
        }
    }
    
    function getTrade(uint256 _tradeId) external view returns (address, address, address, uint256, State, string memory) {
        EscrowTrade storage trade = trades[_tradeId];
        return (trade.buyer, trade.seller, trade.arbiter, trade.amount, trade.state, trade.description);
    }
}
''',
        "interactions": ["createTrade", "releaseFunds", "refundBuyer", "disputeTrade"]
    },
    
    "governance": {
        "name": "Governance Token",
        "code": '''
pragma solidity ^0.8.19;

contract GovernanceToken {
    string public name = "GovToken";
    string public symbol = "GOV";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    address public owner;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    struct Proposal {
        string description;
        uint256 votesFor;
        uint256 votesAgainst;
        uint256 deadline;
        bool executed;
        mapping(address => bool) hasVoted;
        mapping(address => uint256) votingPower;
    }
    
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    uint256 public votingPeriod = 7 days;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event ProposalCreated(uint256 indexed proposalId, string description, uint256 deadline);
    event VoteCast(uint256 indexed proposalId, address indexed voter, bool support, uint256 votes);
    event ProposalExecuted(uint256 indexed proposalId);
    
    constructor(uint256 _initialSupply) {
        totalSupply = _initialSupply * 10**decimals;
        balanceOf[msg.sender] = totalSupply;
        owner = msg.sender;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    function transfer(address _to, uint256 _value) external returns (bool) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        emit Transfer(msg.sender, _to, _value);
        return true;
    }
    
    function approve(address _spender, uint256 _value) external returns (bool) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }
    
    function transferFrom(address _from, address _to, uint256 _value) external returns (bool) {
        require(balanceOf[_from] >= _value, "Insufficient balance");
        require(allowance[_from][msg.sender] >= _value, "Insufficient allowance");
        
        balanceOf[_from] -= _value;
        balanceOf[_to] += _value;
        allowance[_from][msg.sender] -= _value;
        
        emit Transfer(_from, _to, _value);
        return true;
    }
    
    function createProposal(string memory _description) external returns (uint256) {
        require(balanceOf[msg.sender] > 0, "Must hold tokens to create proposal");
        
        uint256 proposalId = proposalCount++;
        Proposal storage newProposal = proposals[proposalId];
        newProposal.description = _description;
        newProposal.deadline = block.timestamp + votingPeriod;
        newProposal.executed = false;
        
        emit ProposalCreated(proposalId, _description, newProposal.deadline);
        return proposalId;
    }
    
    function vote(uint256 _proposalId, bool _support) external {
        require(_proposalId < proposalCount, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        require(block.timestamp < proposal.deadline, "Voting period ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        require(balanceOf[msg.sender] > 0, "Must hold tokens to vote");
        
        uint256 votes = balanceOf[msg.sender];
        proposal.hasVoted[msg.sender] = true;
        proposal.votingPower[msg.sender] = votes;
        
        if (_support) {
            proposal.votesFor += votes;
        } else {
            proposal.votesAgainst += votes;
        }
        
        emit VoteCast(_proposalId, msg.sender, _support, votes);
    }
    
    function executeProposal(uint256 _proposalId) external {
        require(_proposalId < proposalCount, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        require(block.timestamp >= proposal.deadline, "Voting period not ended");
        require(!proposal.executed, "Proposal already executed");
        require(proposal.votesFor > proposal.votesAgainst, "Proposal rejected");
        
        proposal.executed = true;
        emit ProposalExecuted(_proposalId);
    }
    
    function getProposal(uint256 _proposalId) external view returns (string memory, uint256, uint256, uint256, bool) {
        require(_proposalId < proposalCount, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        return (proposal.description, proposal.votesFor, proposal.votesAgainst, proposal.deadline, proposal.executed);
    }
}
''',
        "interactions": ["transfer", "createProposal", "vote", "executeProposal"]
    }
}
